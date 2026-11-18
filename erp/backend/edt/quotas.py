"""Quotas horaires d'un EC dans une classe (règles de l'EDT).

Quota total : crédits × 12 h. Plafond par type : heures CM/TD/TP de l'EC
quand elles sont renseignées (> 0). Les séances comptées sont les séances
Confirmée/Reportée, sur leur créneau effectif, cours mutualisés comptés
une seule fois. Ces fonctions sont l'interface que les modules RH et
Finance utiliseront pour les vacations.
"""
from datetime import date

HEURES_PAR_CREDIT = 12
STATUTS_COMPTES = ('Confirmée', 'Reportée')


def heures_max(ec):
    return (ec.credits or 0) * HEURES_PAR_CREDIT


def plafond_type(ec, type_seance):
    valeur = {'CM': ec.heures_cm, 'TD': ec.heures_td, 'TP': ec.heures_tp}.get(type_seance)
    return valeur or None


def _seances(ec, classe, enseignant=None, type_seance=None):
    from edt.models import Seance
    qs = Seance.objects.filter(ec=ec, classe=classe, statut__in=STATUTS_COMPTES)
    if enseignant is not None:
        qs = qs.filter(enseignant=enseignant)
    if type_seance:
        qs = qs.filter(type_seance=type_seance)
    return Seance.dedupliquer_mutualisees(qs)


def _total(seances, exclure=None, passees_seulement=False):
    from edt.models import Seance
    aujourdhui = date.today()
    total = 0.0
    for s in seances:
        if exclure and s.pk == exclure:
            continue
        jour, debut, fin = s.creneau_effectif()
        if passees_seulement and jour and jour > aujourdhui:
            continue
        total += Seance.calculer_duree_effective(debut, fin)
    return total


def heures_consommees(ec, classe, *, enseignant=None, type_seance=None, exclure=None):
    """Heures planifiées (confirmées ou reportées)."""
    return _total(_seances(ec, classe, enseignant, type_seance), exclure=exclure)


def heures_effectuees(ec, classe, *, enseignant=None, type_seance=None):
    """Heures déjà dispensées (séances passées)."""
    return _total(_seances(ec, classe, enseignant, type_seance), passees_seulement=True)


def heures_restantes(ec, classe, *, exclure=None):
    return heures_max(ec) - heures_consommees(ec, classe, exclure=exclure)
