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

from rh.models import HistoriqueVacation, Vacation

APRES_CONFIRMATION = []      # rappel(vacation) : la Finance y crée la ligne de paie (phase 5)
VERIFICATIONS_RETRAIT = []   # rappel(vacation) : lève ValidationError pour refuser (ex. déjà payée)

BLOCAGE_CONTRAT = "Aucun contrat de vacataire de l'enseignant ne couvre la période des séances."


def _cle(ec_id, classe_id, enseignant_id, type_seance):
    return (ec_id, classe_id, enseignant_id, type_seance or None)


class Heures:
    """Heures effectuées, jumelles et dernière séance de plusieurs affectations, en deux requêtes."""

    CHAMPS = ('pk', 'ec_id', 'classe_id', 'enseignant_id', 'type_seance', 'statut', 'seance_liee_id', 'date_seance',
              'heure_debut', 'heure_fin', 'date_report', 'heure_debut_report', 'heure_fin_report')

    def __init__(self, affectations):
        from edt.models import Seance
        from edt.quotas import STATUTS_COMPTES
        self.effectuees = defaultdict(float)
        self.jumelles = defaultdict(float)
        self.derniere = {}
        classes = {a.classe_id for a in affectations}
        aujourdhui = date.today()

        def passee(s):
            jour = s.creneau_effectif()[0]
            return not jour or jour <= aujourdhui

        seances = [s for s in Seance.objects.filter(classe_id__in=classes, statut__in=STATUTS_COMPTES).only(*self.CHAMPS)
                   if passee(s)]
        # Une jumelle n'est déduite que si sa séance principale est elle-même comptée et passée.
        liees = {s.seance_liee_id for s in seances if s.seance_liee_id}
        principales = {p.pk for p in Seance.objects.filter(pk__in=liees, statut__in=STATUTS_COMPTES).only(*self.CHAMPS)
                       if passee(p)} if liees else set()
        for s in seances:
            jour, debut, fin = s.creneau_effectif()
            duree = Seance.calculer_duree_effective(debut, fin)
            for type_seance in {None, s.type_seance}:
                cle = _cle(s.ec_id, s.classe_id, s.enseignant_id, type_seance)
                self.effectuees[cle] += duree
                if s.seance_liee_id in principales:
                    self.jumelles[cle] += duree
                if jour and (cle not in self.derniere or jour > self.derniere[cle]):
                    self.derniere[cle] = jour

    def de(self, a):
        cle = _cle(a.ec_id, a.classe_id, a.enseignant_id, a.type_seance)
        return self.effectuees.get(cle, 0.0), self.jumelles.get(cle, 0.0)

    def derniere_seance(self, a):
        return self.derniere.get(_cle(a.ec_id, a.classe_id, a.enseignant_id, a.type_seance))


def contrats_vacataires(enseignant_ids):
    """{enseignant_id: [contrats de vacataire]}, en une requête (pk enseignant = pk personne)."""
    from rh.models import Contrat
    par = defaultdict(list)
    for c in Contrat.objects.filter(type='vacataire', personne_id__in=list(enseignant_ids)).order_by('date_debut'):
        par[c.personne_id].append(c)
    return par


def contrat_de_la_periode(contrats, jour):
    """Contrat de vacataire qui couvre `jour` (dernière séance faite, sinon aujourd'hui)."""
    for c in contrats:
        if c.date_debut <= jour and (c.date_fin is None or jour <= c.date_fin):
            return c
    return None


def _vacation_de(affectation):
    try:
        return affectation.vacation
    except ObjectDoesNotExist:
        return None


def etat(affectation, heures=None, jour=None, contrats=None):
    """État de vacation d'une affectation (heures, terminée, contrat, confirmable, vacation).

    Le contrat retenu (blocage et taux) est celui de vacataire qui couvre la dernière séance faite,
    à défaut celui du jour : une vacation finie se confirme même après la fin du contrat.
    `heures` (Heures) et `contrats` (contrats_vacataires) évitent les requêtes par ligne.
    """
    heures = heures or Heures([affectation])
    effectuees, jumelles = heures.de(affectation)
    if contrats is None:
        contrats = contrats_vacataires([affectation.enseignant_id])
    reference = heures.derniere_seance(affectation) or jour or timezone.localdate()
    contrat = contrat_de_la_periode(contrats.get(affectation.enseignant_id, []), reference)
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
    if abs(d) >= 10000:
        raise ValidationError({champ: 'Nombre d’heures trop grand.'})
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
    # Verrou : deux retraits simultanés (ou un objet périmé) ne retirent pas deux fois.
    vacation = Vacation.objects.select_for_update().select_related('affectation').filter(pk=vacation.pk).first()
    if vacation is None:
        raise ValidationError("Cette vacation n'est plus confirmée.")
    for verification in list(VERIFICATIONS_RETRAIT):
        verification(vacation)
    HistoriqueVacation.objects.create(affectation=vacation.affectation, action='retrait',
                                      heures_retenues=vacation.heures_retenues, montant=vacation.montant,
                                      motif=motif, par=par, le=timezone.now())
    vacation.delete()


CHAMPS_FIGES = ('enseignant_id', 'ec_id', 'classe_id', 'type_seance', 'heures_prevues')


def refuser_modification_si_confirmee(affectation):
    """Branché sur edt.models.VERIFICATIONS_AFFECTATION : une affectation confirmée ne change plus."""
    if not affectation.pk or not Vacation.objects.filter(affectation_id=affectation.pk).exists():
        return
    from edt.models import AffectationEC
    avant = AffectationEC.objects.filter(pk=affectation.pk).values(*CHAMPS_FIGES).first()
    if avant and any(avant[c] != getattr(affectation, c) for c in CHAMPS_FIGES):
        raise ValidationError("La vacation de cette affectation est confirmée par la faculté : retirez d'abord la "
                              "confirmation pour la modifier.")
