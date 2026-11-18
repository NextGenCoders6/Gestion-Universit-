"""Dossiers de frais : montant depuis le tarif, échéancier mensuel, état des mensualités."""
from datetime import date
from decimal import ROUND_DOWN, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from finance.models import EcheanceFrais, FraisScolarite, Tarif

PAR_DEFAUT = {'nombre_mensualites': 10, 'jour_echeance': 5}


def _mois_suivant(annee, mois):
    return (annee + 1, 1) if mois == 12 else (annee, mois + 1)


def echeancier(montant, nombre, premier_mois, jour):
    """[(mois 'AAAA-MM', date limite, montant)] : mensualités égales, la dernière prend l'arrondi.

    La mensualité du mois M est due le `jour` du mois M+1.
    """
    montant = Decimal(montant)
    if montant <= 0 or nombre < 1:
        return []
    base = (montant / nombre).quantize(Decimal('1'), rounding=ROUND_DOWN)
    annee, mois = (int(x) for x in premier_mois.split('-'))
    lignes = []
    for i in range(nombre):
        a_lim, m_lim = _mois_suivant(annee, mois)
        part = base if i < nombre - 1 else montant - base * (nombre - 1)
        lignes.append((f'{annee:04d}-{mois:02d}', date(a_lim, m_lim, jour), part))
        annee, mois = _mois_suivant(annee, mois)
    return lignes


def tarif_de(inscription):
    return Tarif.objects.filter(annee_id=inscription.annee_id, parcours_id=inscription.classe.parcours_id).first()


def _modalite(dossier, tarif=None):
    """(nombre, premier mois, jour) : celle du tarif, sinon celle par défaut de l'année."""
    tarif = tarif or tarif_de(dossier.inscription)
    if tarif is not None:
        return tarif.nombre_mensualites, tarif.premier_mois, tarif.jour_echeance
    return (PAR_DEFAUT['nombre_mensualites'], f'{dossier.inscription.annee.date_debut.year}-10',
            PAR_DEFAUT['jour_echeance'])


def _remplacer_echeances(dossier, lignes):
    dossier.echeances.all().delete()
    EcheanceFrais.objects.bulk_create([EcheanceFrais(dossier=dossier, numero=i, mois=m, date_limite=d, montant=x)
                                       for i, (m, d, x) in enumerate(lignes, start=1)])


def regenerer_echeances(dossier, tarif=None):
    _remplacer_echeances(dossier, echeancier(dossier.montant_du, *_modalite(dossier, tarif)))


def redistribuer(dossier, montant):
    """Mêmes mois et dates, montants mis à l'échelle de `montant` (la dernière mensualité prend l'arrondi).

    Garde les proportions d'un échéancier adapté ; sans échéances, en crée selon la modalité.
    """
    actuelles = list(dossier.echeances.all())
    total = sum((e.montant for e in actuelles), Decimal('0'))
    if not actuelles or total <= 0:
        regenerer_echeances(dossier)
        return
    if montant <= 0:
        _remplacer_echeances(dossier, [])
        return
    parts = [(e.montant * montant / total).quantize(Decimal('1'), rounding=ROUND_DOWN) for e in actuelles[:-1]]
    parts.append(montant - sum(parts, Decimal('0')))
    _remplacer_echeances(dossier, [(e.mois, e.date_limite, p) for e, p in zip(actuelles, parts)])


@transaction.atomic
def creer_dossier(inscription):
    """Rappel APRES_INSCRIPTION : dossier au tarif du niveau (0 sans tarif), avec son échéancier."""
    dossier, cree = FraisScolarite.objects.get_or_create(inscription=inscription)
    if cree:
        tarif = tarif_de(inscription)
        dossier.montant_du = tarif.montant if tarif else Decimal('0')
        dossier.save()
        regenerer_echeances(dossier, tarif)
    return dossier


@transaction.atomic
def appliquer_tarif(tarif):
    """Recalcule les dossiers de l'année et du niveau, sauf ceux dont le montant a été fixé à la main."""
    dossiers = FraisScolarite.objects.select_for_update().filter(
        inscription__annee_id=tarif.annee_id, inscription__classe__parcours_id=tarif.parcours_id, montant_ajuste=False)
    for dossier in dossiers.select_related('inscription__annee', 'inscription__classe'):
        dossier.montant_du = tarif.montant
        dossier.save(update_fields=['montant_du'])
        if dossier.echeancier_adapte:
            redistribuer(dossier, tarif.montant)    # la somme des mensualités reste égale au montant dû
        else:
            regenerer_echeances(dossier, tarif)


@transaction.atomic
def ajuster(dossier, montant, par=None):
    """Montant fixé à la main : le tarif ne le change plus ; échéancier redistribué sur les mêmes mois."""
    montant = Decimal(montant)
    if montant < 0:
        raise ValidationError({'montant': 'Le montant ne peut pas être négatif.'})
    dossier = FraisScolarite.objects.select_for_update().get(pk=dossier.pk)
    dossier.montant_du = montant
    dossier.montant_ajuste = True
    dossier.save()
    redistribuer(dossier, montant)
    return dossier


@transaction.atomic
def adapter_echeancier(dossier, lignes, par=None):
    """Échéancier fixé à la main : somme = montant dû, dates strictement croissantes."""
    from finance.models import MOIS
    for m, d, _ in lignes:
        if not MOIS.match(str(m or '')):
            raise ValidationError({'echeances': f'Mois invalide « {m} » (AAAA-MM attendu).'})
        if not isinstance(d, date):
            raise ValidationError({'echeances': 'Chaque mensualité a une date limite.'})
    lignes = [(m, d, Decimal(x)) for m, d, x in lignes]
    if any(x <= 0 for _, _, x in lignes):
        raise ValidationError({'echeances': 'Chaque mensualité doit être positive.'})
    if sum((x for _, _, x in lignes), Decimal('0')) != dossier.montant_du:
        raise ValidationError({'echeances': f'La somme des mensualités doit être égale au montant dû '
                                            f'({dossier.montant_du}).'})
    dates = [d for _, d, _ in lignes]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise ValidationError({'echeances': 'Les dates limites doivent être croissantes.'})
    dossier = FraisScolarite.objects.select_for_update().get(pk=dossier.pk)
    _remplacer_echeances(dossier, lignes)
    dossier.echeancier_adapte = True
    dossier.save(update_fields=['echeancier_adapte'])
    return dossier


def etat_echeances(dossier, jour=None, echeances=None):
    """État de chaque mensualité ; le payé couvre les échéances dans l'ordre."""
    jour = jour or timezone.localdate()
    reste = dossier.montant_paye
    etats = []
    for e in (echeances if echeances is not None else dossier.echeances.all()):
        paye = min(reste, e.montant)
        reste -= paye
        if paye >= e.montant:
            etat = 'payee'
        elif e.date_limite < jour:
            etat = 'en_retard'
        elif paye > 0:
            etat = 'partielle'
        else:
            etat = 'a_venir'
        etats.append({'numero': e.numero, 'mois': e.mois, 'date_limite': e.date_limite, 'montant': e.montant,
                      'paye': paye, 'etat': etat})
    return etats


def montant_en_retard(dossier, jour=None, echeances=None):
    return sum((e['montant'] - e['paye'] for e in etat_echeances(dossier, jour, echeances) if e['etat'] == 'en_retard'),
               Decimal('0'))


def en_retard(dossier, jour=None, echeances=None):
    return montant_en_retard(dossier, jour, echeances) > 0


def prochaine_echeance(dossier, jour=None, echeances=None):
    return next((e for e in etat_echeances(dossier, jour, echeances) if e['etat'] != 'payee'), None)


def creer_dossiers_manquants():
    """Dossiers des inscriptions antérieures à la Finance ; renvoie le nombre créé."""
    from scolarite.models import Inscription
    manquantes = Inscription.objects.filter(frais__isnull=True).select_related('classe', 'annee')
    return sum(1 for i in manquantes if creer_dossier(i))


def motif_masquage_resultats(inscription):
    """Branché sur scolarite.inscriptions.MOTIFS_MASQUAGE_RESULTATS (décision 4) : retard ⇒ résultats masqués."""
    dossier = FraisScolarite.objects.filter(inscription=inscription).prefetch_related('echeances').first()
    if dossier is None:
        return None
    retard = montant_en_retard(dossier, echeances=list(dossier.echeances.all()))
    if retard <= 0:
        return None
    return (f'Vos moyennes et décisions de {inscription.annee.libelle} s’afficheront quand votre mensualité échue '
            f'sera réglée (reste à régler : {retard:,.0f} FCFA).'.replace(',', ' '))


def recalculer_dossier(inscription):
    """Rappel APRES_CHANGEMENT_CLASSE : le dossier suit le tarif du nouveau niveau (sauf montant fixé à la main)."""
    dossier = FraisScolarite.objects.filter(inscription=inscription).first()
    if dossier is None:
        creer_dossier(inscription)
        return
    if dossier.montant_ajuste:
        return
    tarif = tarif_de(inscription)
    dossier.montant_du = tarif.montant if tarif else Decimal('0')
    dossier.save(update_fields=['montant_du'])
    if dossier.echeancier_adapte:
        redistribuer(dossier, dossier.montant_du)
    else:
        regenerer_echeances(dossier, tarif)
