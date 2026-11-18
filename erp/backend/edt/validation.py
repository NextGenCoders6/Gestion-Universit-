"""Règles de validation des séances et affectations.

Port de uccb_backend/EDT_app/validation_seance.py sur le référentiel du socle :
- l'année d'une séance est celle de sa classe (plus de contrôle de cohérence) ;
- « module dans le semestre de la classe » devient « EC au programme de la classe » ;
- les bornes viennent de la période (1 ou 2) du semestre de l'EC ;
- les quotas se comptent par (EC, classe) — voir edt/quotas.py ;
- une séance mutualisée partage enseignant et créneau avec sa jumelle ; les EC
  peuvent différer (chaque classe a le sien).
"""
from datetime import datetime, date as date_type, time as time_type

from django.core.exceptions import ValidationError
from django.db.models import Q

MIN_HEURE_DEBUT = time_type(9, 0)
HEURE_FIN_MAX = time_type(16, 20)
MAX_HEURES_JOUR = 6
PAUSE_DEBUT = time_type(11, 0)
PAUSE_FIN = time_type(11, 15)
PAUSE_MERIDIENNE_DEBUT = time_type(13, 15)
PAUSE_MERIDIENNE_FIN = time_type(14, 15)
BLOCS_JOURNEE = [
    (time_type(9, 0), time_type(11, 0)),
    (time_type(11, 15), time_type(13, 15)),
    (time_type(14, 15), time_type(16, 15)),
]


def _h(t):
    return t.strftime('%Hh%M')


def duree_effective(heure_debut, heure_fin):
    debut = datetime.combine(date_type.today(), heure_debut)
    fin = datetime.combine(date_type.today(), heure_fin)
    duree = fin - debut
    p_debut = datetime.combine(date_type.today(), PAUSE_DEBUT)
    p_fin = datetime.combine(date_type.today(), PAUSE_FIN)
    if debut < p_fin and fin > p_debut:
        duree -= min(fin, p_fin) - max(debut, p_debut)
    return duree.total_seconds() / 3600


def q_jour_effectif(debut=None, fin=None):
    """Séances dont le jour effectif (report complet, sinon jour d'origine) est dans [debut, fin]."""
    reportee = Q(statut='Reportée', date_report__isnull=False, heure_debut_report__isnull=False,
                 heure_fin_report__isnull=False)
    sur_origine, sur_report = Q(), Q()
    if debut:
        sur_origine &= Q(date_seance__gte=debut)
        sur_report &= Q(date_report__gte=debut)
    if fin:
        sur_origine &= Q(date_seance__lte=fin)
        sur_report &= Q(date_report__lte=fin)
    return (reportee & sur_report) | (~reportee & sur_origine)


def q_occupe_creneau(jour, heure_debut, heure_fin):
    """Séances qui occupent réellement ce créneau (confirmées, ou reportées sur leur créneau effectif)."""
    origine = Q(date_seance=jour, heure_debut__lt=heure_fin, heure_fin__gt=heure_debut)
    report = Q(date_report=jour, heure_debut_report__lt=heure_fin, heure_fin_report__gt=heure_debut)
    report_incomplet = Q(heure_debut_report__isnull=True) | Q(heure_fin_report__isnull=True)
    return (Q(statut='Confirmée') & origine) | (Q(statut='Reportée') & report) | (
        Q(statut='Reportée') & report_incomplet & origine)


# ── Créneau ──────────────────────────────────────────────────────

def valider_hors_pause_meridienne(heure_debut, heure_fin, champ='heure_debut'):
    if heure_debut and heure_fin and heure_debut < PAUSE_MERIDIENNE_FIN and heure_fin > PAUSE_MERIDIENNE_DEBUT:
        raise ValidationError({champ: (
            f'Une séance ne peut pas empiéter sur la pause méridienne '
            f'({_h(PAUSE_MERIDIENNE_DEBUT)}–{_h(PAUSE_MERIDIENNE_FIN)}).'
        )})


def valider_horaires(heure_debut, heure_fin):
    if not heure_debut or not heure_fin:
        raise ValidationError({'heure_debut': 'Horaires obligatoires.'})
    if heure_debut < MIN_HEURE_DEBUT:
        raise ValidationError({'heure_debut': f'Les séances ne peuvent pas commencer avant {_h(MIN_HEURE_DEBUT)}.'})
    if heure_fin > HEURE_FIN_MAX:
        raise ValidationError({'heure_fin': f"L'heure de fin maximale est {_h(HEURE_FIN_MAX)}."})
    if heure_debut >= heure_fin:
        raise ValidationError({'heure_fin': "L'heure de début doit être avant la fin."})
    valider_hors_pause_meridienne(heure_debut, heure_fin)


def valider_dimanche(jour, champ='date_seance'):
    if jour and jour.weekday() == 6:
        raise ValidationError({champ: 'Impossible de planifier une séance un dimanche.'})


# ── Calendrier et programme ──────────────────────────────────────

def valider_annee_non_archivee(annee):
    if annee and annee.statut == 'archivee':
        raise ValidationError(f"L'année {annee} est archivée : son emploi du temps ne peut plus être modifié.")


def valider_ec_dans_classe(ec, classe):
    """L'EC appartient au programme de la classe : même portail/filière et semestre du niveau."""
    ue = ec.ue
    meme_rattachement = (ue.portail_id and ue.portail_id == classe.portail_id) or (
        ue.filiere_id and ue.filiere_id == classe.filiere_id)
    if not meme_rattachement or ue.semestre not in classe.semestres:
        raise ValidationError({'ec': (
            f"L'EC {ec.code} ({ue.semestre}) ne fait pas partie du programme de la classe {classe.libelle}."
        )})


def periode_de(classe, ec):
    """Période calendaire (1 ou 2) de l'EC dans l'année de la classe ; ValidationError si elle manque."""
    numero = ec.ue.periode_numero
    periode = classe.annee.periodes.filter(numero=numero).first()
    if periode is None:
        raise ValidationError({'date_seance': (
            f"La période Semestre {numero} de {classe.annee.libelle} n'est pas définie. "
            "Renseignez ses dates dans Paramètres › Référentiel."
        )})
    return periode


def valider_bornes_periode(jour, classe, ec, champ='date_seance'):
    periode = periode_de(classe, ec)
    if not (periode.date_debut <= jour <= periode.date_fin):
        raise ValidationError({champ: (
            f'La date est hors du semestre {periode.numero} '
            f'({periode.date_debut:%d/%m/%Y} → {periode.date_fin:%d/%m/%Y}).'
        )})


def valider_departement(enseignant, ec, classe):
    """L'enseignant est du département de l'EC, sauf affectation hors département sur cet EC et cette classe."""
    if enseignant.departement_id == ec.departement_id:
        return
    from edt.models import AffectationEC
    if AffectationEC.objects.filter(ec=ec, classe=classe, enseignant=enseignant, hors_departement=True).exists():
        return
    raise ValidationError({'enseignant': (
        f"L'enseignant ({enseignant.departement}) n'est pas du département qui porte l'EC ({ec.departement})."
    )})


# ── Conflits ─────────────────────────────────────────────────────

def valider_conflit_enseignant(enseignant, jour, debut, fin, pk, pks_exemptes=()):
    from edt.models import Seance
    if not (enseignant and jour and debut and fin):
        return
    qs = Seance.objects.filter(q_occupe_creneau(jour, debut, fin), enseignant=enseignant).exclude(pk=pk)
    if pks_exemptes:
        qs = qs.exclude(pk__in=pks_exemptes)
    if qs.exists():
        raise ValidationError(f"L'enseignant a déjà une séance le {jour:%d/%m/%Y} sur ce créneau.")


def valider_conflit_classe(classe, jour, debut, fin, pk):
    from edt.models import Seance
    if not (classe and jour and debut and fin):
        return
    if Seance.objects.filter(q_occupe_creneau(jour, debut, fin), classe=classe).exclude(pk=pk).exists():
        raise ValidationError(f'La classe a déjà une séance le {jour:%d/%m/%Y} sur ce créneau.')


def valider_seance_liee(seance):
    """Un cours mutualisé partage l'enseignant et le créneau de sa séance jumelle."""
    jumelles = []
    if seance.seance_liee_id:
        jumelles.append(seance.seance_liee)
    if seance.pk:
        jumelles.extend(seance.seances_associees.all())
    # Déplacement groupé d'une paire : les jumelles modifiées en mémoire priment sur la base.
    en_memoire = {j.pk: j for j in getattr(seance, '_jumelles_en_cours', [])}
    jumelles = [en_memoire.get(j.pk, j) for j in jumelles]
    for j in jumelles:
        if j.enseignant_id != seance.enseignant_id or j.creneau_effectif() != seance.creneau_effectif():
            raise ValidationError({'seance_liee': (
                'Une séance mutualisée doit avoir le même enseignant et le même créneau que sa séance liée.'
            )})
        if j.classe_id == seance.classe_id:
            raise ValidationError({'seance_liee': 'Une séance mutualisée concerne une autre classe.'})


def valider_doublon(statut, classe, ec, jour, debut, fin, pk):
    from edt.models import Seance
    if statut != 'brouillon' or not (classe and ec and jour and debut and fin):
        return
    if Seance.objects.filter(classe=classe, ec=ec, date_seance=jour, heure_debut=debut, heure_fin=fin,
                             statut__in=('brouillon', 'Confirmée')).exclude(pk=pk).exists():
        raise ValidationError('Cette séance existe déjà : même EC, même classe, même créneau.')


# ── Volumes ──────────────────────────────────────────────────────

def valider_volume_ec(ec, classe, duree, pk):
    from edt import quotas
    restantes = quotas.heures_restantes(ec, classe, exclure=pk)
    if duree > restantes:
        raise ValidationError(
            f"Cette séance ({duree:g} h) dépasse le volume restant de l'EC {ec.code} dans cette classe "
            f'({restantes:g} h restantes sur {quotas.heures_max(ec)} h).'
        )


def valider_affectation(ec, classe, enseignant, type_seance, duree, pk):
    from edt.models import AffectationEC
    if not (ec and classe and enseignant and type_seance):
        return
    affectations = AffectationEC.objects.filter(ec=ec, classe=classe, enseignant=enseignant)
    affectation = (affectations.filter(type_seance=type_seance).first()
                   or affectations.filter(type_seance__isnull=True).first())
    if affectation is None:
        if AffectationEC.objects.filter(ec=ec, classe=classe).exists():
            raise ValidationError({'enseignant': (
                "Cet enseignant n'est pas affecté sur cet EC dans cette classe "
                '(ni pour ce type de séance, ni de manière générique).'
            )})
        return  # aucune affectation déclarée : pas de contrôle (comme l'EDT)
    restantes = affectation.heures_restantes(exclure=pk)
    if duree > restantes:
        raise ValidationError(
            f"Cette séance ({duree:g} h) dépasse le volume restant de l'affectation de cet enseignant "
            f'({affectation.type_seance or "générique"} : {restantes:g} h restantes sur '
            f'{affectation.heures_prevues:g} h).'
        )


def valider_volume_journalier(classe, jour, debut, fin, pk):
    from edt.models import Seance
    if not (classe and jour and debut and fin):
        return
    du_jour = Seance.objects.filter(classe=classe).filter(
        Q(statut='Confirmée', date_seance=jour) | Q(statut='Reportée', date_report=jour)
    ).exclude(pk=pk)
    total = duree_effective(debut, fin)
    for s in du_jour:
        _, d, f = s.creneau_effectif()
        total += duree_effective(d, f)
    if total > MAX_HEURES_JOUR:
        raise ValidationError(
            f'Le volume journalier de la classe dépasse {MAX_HEURES_JOUR} h (total calculé : {total:.2f} h).'
        )


def valider_creneau_report(seance):
    if not (seance.date_report and seance.heure_debut_report and seance.heure_fin_report):
        raise ValidationError({'date_report': 'Les données de report sont incomplètes.'})
    valider_dimanche(seance.date_report, champ='date_report')
    if seance.heure_debut_report < MIN_HEURE_DEBUT:
        raise ValidationError({'heure_debut_report': f'Le report ne peut pas commencer avant {_h(MIN_HEURE_DEBUT)}.'})
    if seance.heure_fin_report > HEURE_FIN_MAX:
        raise ValidationError({'heure_fin_report': f'Le report ne peut pas finir après {_h(HEURE_FIN_MAX)}.'})
    if seance.heure_debut_report >= seance.heure_fin_report:
        raise ValidationError({'heure_fin_report': "L'heure de début du report doit être avant la fin."})
    valider_hors_pause_meridienne(seance.heure_debut_report, seance.heure_fin_report, champ='heure_debut_report')
    valider_bornes_periode(seance.date_report, seance.classe, seance.ec, champ='date_report')


# ── Archivage d'une année ────────────────────────────────────────

def refuser_archivage_avec_seances_futures(annee):
    from edt.models import Seance
    if not annee.pk:
        return
    futures = Seance.objects.filter(classe__annee=annee, statut='Confirmée', date_seance__gt=date_type.today())
    if futures.exists():
        raise ValidationError({'statut': (
            f"Impossible d'archiver cette année : elle contient {futures.count()} séance(s) confirmée(s) à venir."
        )})
