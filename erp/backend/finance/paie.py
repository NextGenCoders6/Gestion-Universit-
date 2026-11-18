"""Paie : salaires mensuels des contrats permanents, vacations confirmées, paiements et annulations."""
import calendar
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from finance import journal
from finance.models import MOIS, Paie, PaiementPaie


def bornes_mois(mois):
    if not MOIS.match(mois or ''):
        raise ValidationError({'mois': 'Mois invalide (AAAA-MM attendu).'})
    annee, m = (int(x) for x in mois.split('-'))
    return date(annee, m, 1), date(annee, m, calendar.monthrange(annee, m)[1])


@transaction.atomic
def generer_salaires(mois, par=None):
    """Une ligne par contrat permanent en cours au moins un jour du mois ; relancer ne double rien."""
    from rh.models import Contrat
    debut, fin = bornes_mois(mois)
    contrats = Contrat.objects.filter(type='permanent', date_debut__lte=fin).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=debut)).select_related('personne')
    creees = existantes = 0
    for contrat in contrats:
        _, cree = Paie.objects.get_or_create(contrat=contrat, mois=mois, defaults={
            'origine': 'salaire', 'personne': contrat.personne, 'montant_du': contrat.salaire_mensuel})
        creees += cree
        existantes += not cree
    return creees, existantes


def creer_ligne_vacation(vacation):
    """Rappel rh.vacations.APRES_CONFIRMATION."""
    return Paie.objects.create(origine='vacation', personne=vacation.contrat.personne, contrat=vacation.contrat,
                               vacation=vacation, montant_du=vacation.montant)


def refuser_retrait_si_payee(vacation):
    """Rappel rh.vacations.VERIFICATIONS_RETRAIT : une vacation payée ne se retire pas."""
    if PaiementPaie.objects.filter(paie__vacation=vacation, annule=False).exists():
        raise ValidationError('Cette vacation a déjà reçu un paiement : annulez d’abord le paiement en Finance.')


def libelle_paie(p):
    personne = p.personne
    matricule = getattr(getattr(personne, 'enseignant', None), 'matricule', None) or \
        getattr(getattr(personne, 'employe', None), 'matricule', '')
    if p.origine == 'salaire':
        return f'Salaire {p.mois} — {personne.nom_complet} ({matricule})'
    a = p.vacation.affectation
    return f'Vacation — {personne.nom_complet} ({matricule}), {a.ec.code} {a.classe.libelle}'


@transaction.atomic
def payer(paie, montant, mode, *, date=None, reference='', par=None):
    montant = journal.montant_valide(montant)
    mode = journal.mode_valide(mode)
    jour = journal.date_valide(date)
    paie = Paie.objects.select_for_update().select_related(
        'personne', 'vacation__affectation__ec', 'vacation__affectation__classe').get(pk=paie.pk)
    if paie.reste <= 0:
        raise ValidationError({'montant': 'Cette ligne de paie est déjà réglée.'})
    if montant > paie.reste:
        raise ValidationError({'montant': f'Le montant dépasse le reste à payer ({paie.reste:.0f} FCFA).'})
    operation = journal.ecrire(libelle_paie(paie), -montant, paie.origine, jour, par)
    paiement = PaiementPaie.objects.create(paie=paie, montant=montant, mode=mode, date=jour,
                                           reference=(reference or '')[:60], operation=operation, par=par)
    Paie.objects.filter(pk=paie.pk).update(montant_paye=F('montant_paye') + montant)
    return paiement


@transaction.atomic
def annuler_paiement_paie(paiement, motif, par=None):
    motif = (motif or '').strip()
    if not motif:
        raise ValidationError({'motif': "Indiquez le motif de l'annulation."})
    paiement = PaiementPaie.objects.select_for_update().select_related('operation').get(pk=paiement.pk)
    if paiement.annule:
        raise ValidationError('Ce paiement est déjà annulé.')
    Paie.objects.select_for_update().get(pk=paiement.paie_id)
    contre = journal.ecrire(f'Annulation — {paiement.operation.libelle} ({motif})', paiement.montant, 'annulation',
                            timezone.localdate(), par, annule=paiement.operation)
    paiement.annule = True
    paiement.motif_annulation = motif[:255]
    paiement.save(update_fields=['annule', 'motif_annulation'])
    Paie.objects.filter(pk=paiement.paie_id).update(montant_paye=F('montant_paye') - paiement.montant)
    return contre


@transaction.atomic
def ajuster(paie, montant, par=None):
    montant = journal.montant_valide(montant, positif=False)
    if montant < 0:
        raise ValidationError({'montant': 'Le montant ne peut pas être négatif.'})
    paie = Paie.objects.select_for_update().get(pk=paie.pk)
    if paie.paiements.filter(annule=False).exists():
        raise ValidationError('Cette ligne a déjà reçu un paiement : annulez-le avant de changer le montant.')
    paie.montant_du = montant
    paie.montant_ajuste = True
    paie.save(update_fields=['montant_du', 'montant_ajuste'])
    return paie
