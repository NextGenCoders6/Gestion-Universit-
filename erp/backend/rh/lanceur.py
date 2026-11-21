"""Résumé RH du launchpad : contrats arrivant à échéance sous 30 jours, vacations à confirmer.

Le compte des vacations relit les séances des classes concernées : il est mis en cache quelques minutes.
Il ne dépend pas des paramètres de l'URL du lanceur (la RH voit toutes les facultés et l'année en cours).
"""
from types import SimpleNamespace

from django.core.cache import cache

from core.lanceur import entree
from rh.contrats import contrats_a_echeance

DUREE_CACHE = 120  # secondes


def _vacations(n):
    if n == 0:
        return 'Aucune vacation à confirmer'
    return f"{n} vacation{'s' if n > 1 else ''} à confirmer"


def _vacations_a_confirmer(user):
    from rh.views import affectations_de_vacataires, lignes_vacations
    affectations = affectations_de_vacataires(SimpleNamespace(user=user, query_params={}))
    return len(lignes_vacations(SimpleNamespace(user=user, query_params={'etat': 'a_confirmer'}), affectations))


def resume(request):
    echeances = contrats_a_echeance(30).count()
    a_confirmer = cache.get_or_set('lanceur:rh:vacations', lambda: _vacations_a_confirmer(request.user), DUREE_CACHE)
    return entree('rh', valeur=echeances, libelle='contrats à échéance', detail=_vacations(a_confirmer),
                  ton='alerte' if echeances else 'normal')
