"""Vacations : une affectation EDT d'un vacataire, terminée puis confirmée par la faculté.

- Heures effectuées : séances confirmées ou reportées, dont le jour effectif est passé.
- Terminée : heures effectuées ≥ heures prévues.
- Heures dues : heures effectuées moins celles des séances « jumelles » d'un cours
  mutualisé (séance liée à celle d'une autre classe, au même créneau) : le vacataire
  est payé une fois par créneau, sur la classe de la séance principale.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.utils import timezone

from rh.contrats import contrat_en_cours
from rh.models import HistoriqueVacation, Vacation

APRES_CONFIRMATION = []      # rappel(vacation) : la Finance y crée la ligne de paie (phase 5)
VERIFICATIONS_RETRAIT = []   # rappel(vacation) : lève ValidationError pour refuser (ex. déjà payée)

BLOCAGE_CONTRAT = "L'enseignant n'a pas de contrat de vacataire en cours."


def _cle(ec_id, classe_id, enseignant_id, type_seance):
    return (ec_id, classe_id, enseignant_id, type_seance or None)


class Heures:
    """Heures effectuées et jumelles de plusieurs affectations, en une requête."""

    def __init__(self, affectations):
        from edt.models import Seance
        from edt.quotas import STATUTS_COMPTES
        self.effectuees = defaultdict(float)
        self.jumelles = defaultdict(float)
        classes = {a.classe_id for a in affectations}
        aujourdhui = date.today()
        seances = Seance.objects.filter(classe_id__in=classes, statut__in=STATUTS_COMPTES).only(
            'pk', 'ec_id', 'classe_id', 'enseignant_id', 'type_seance', 'statut', 'seance_liee_id', 'date_seance',
            'heure_debut', 'heure_fin', 'date_report', 'heure_debut_report', 'heure_fin_report')
        for s in seances:
            jour, debut, fin = s.creneau_effectif()
            if jour and jour > aujourdhui:
                continue
            duree = Seance.calculer_duree_effective(debut, fin)
            for type_seance in {None, s.type_seance}:
                cle = _cle(s.ec_id, s.classe_id, s.enseignant_id, type_seance)
                self.effectuees[cle] += duree
                if s.seance_liee_id:
                    self.jumelles[cle] += duree

    def de(self, a):
        cle = _cle(a.ec_id, a.classe_id, a.enseignant_id, a.type_seance)
        return self.effectuees.get(cle, 0.0), self.jumelles.get(cle, 0.0)


def contrats_vacataires_en_cours(enseignant_ids, jour=None):
    """{enseignant_id: contrat de vacataire en cours}, en une requête (pk enseignant = pk personne)."""
    from rh.contrats import q_en_cours
    from rh.models import Contrat
    qs = Contrat.objects.filter(q_en_cours(jour or timezone.localdate()), type='vacataire',
                                personne_id__in=list(enseignant_ids))
    return {c.personne_id: c for c in qs}


def _vacation_de(affectation):
    try:
        return affectation.vacation
    except ObjectDoesNotExist:
        return None


def etat(affectation, heures=None, jour=None, contrats=None):
    """État de vacation d'une affectation (heures, terminée, contrat, confirmable, vacation).

    `heures` (Heures) et `contrats` (contrats_vacataires_en_cours) évitent les requêtes par ligne.
    """
    heures = heures or Heures([affectation])
    effectuees, jumelles = heures.de(affectation)
    if contrats is None:
        contrat = contrat_en_cours(affectation.enseignant.personne, jour, type='vacataire')
    else:
        contrat = contrats.get(affectation.enseignant_id)
    vacation = _vacation_de(affectation)
    blocage = None
    if vacation is not None:
        blocage = 'Vacation déjà confirmée.'
    elif contrat is None:
        blocage = BLOCAGE_CONTRAT
    return {
        'heures_prevues': float(affectation.heures_prevues), 'heures_effectuees': effectuees,
        'heures_jumelles': jumelles, 'heures_dues': max(0.0, effectuees - jumelles),
        'terminee': effectuees >= float(affectation.heures_prevues), 'contrat': contrat,
        'confirmable': blocage is None, 'motif_blocage': blocage, 'vacation': vacation,
    }


def _decimal(valeur, champ):
    try:
        d = Decimal(str(valeur).replace(',', '.'))
    except (InvalidOperation, ValueError):
        raise ValidationError({champ: 'Nombre d’heures invalide.'})
    if not d.is_finite():
        raise ValidationError({champ: 'Nombre d’heures invalide.'})
    return d


@transaction.atomic
def confirmer(affectation, *, heures_retenues=None, motif='', par=None):
    from edt.models import AffectationEC
    affectation = AffectationEC.objects.select_for_update().select_related('enseignant__personne').get(pk=affectation.pk)
    e = etat(affectation)
    if e['vacation'] is not None:
        raise ValidationError('Cette vacation est déjà confirmée.')
    if e['contrat'] is None:
        raise ValidationError(BLOCAGE_CONTRAT)
    motif = (motif or '').strip()
    dues = Decimal(str(e['heures_dues'])).quantize(Decimal('0.01'))
    retenues = dues if heures_retenues in (None, '') else _decimal(heures_retenues, 'heures_retenues').quantize(
        Decimal('0.01'))
    if retenues < 0:
        raise ValidationError({'heures_retenues': 'Les heures retenues ne peuvent pas être négatives.'})
    if not motif and retenues != dues:
        raise ValidationError({'motif': f'Indiquez le motif : les heures retenues ({retenues} h) diffèrent des '
                                        f'heures dues ({dues} h).'})
    if not motif and not e['terminee']:
        raise ValidationError({'motif': "L'affectation n'est pas terminée : indiquez le motif de la confirmation."})
    taux = e['contrat'].taux_horaire
    montant = (retenues * taux).quantize(Decimal('0.01'))
    vacation = Vacation.objects.create(
        affectation=affectation, contrat=e['contrat'], heures_effectuees=Decimal(str(e['heures_effectuees'])),
        heures_retenues=retenues, motif=motif, taux_horaire=taux, montant=montant, confirmee_par=par)
    HistoriqueVacation.objects.create(affectation=affectation, action='confirmation', heures_retenues=retenues,
                                      montant=montant, motif=motif, par=par)
    for rappel in list(APRES_CONFIRMATION):
        rappel(vacation)
    return vacation


@transaction.atomic
def retirer(vacation, *, motif, par=None):
    motif = (motif or '').strip()
    if not motif:
        raise ValidationError({'motif': 'Indiquez le motif du retrait de la confirmation.'})
    for verification in list(VERIFICATIONS_RETRAIT):
        verification(vacation)
    HistoriqueVacation.objects.create(affectation=vacation.affectation, action='retrait',
                                      heures_retenues=vacation.heures_retenues, montant=vacation.montant,
                                      motif=motif, par=par, le=timezone.now())
    vacation.delete()
