"""Résumé Finance du launchpad : part des frais de l'année en cours déjà encaissée.

Le calcul parcourt tous les dossiers de l'année : il est mis en cache quelques minutes, identique
pour tous les comptes Finance (le tableau de bord, lui, recalcule à chaque appel).
"""
from django.core.cache import cache

from core.lanceur import entree
from core.models import AnneeAcademique
from finance.tableau import indicateurs_frais


def _retards(n):
    if n == 0:
        return 'Aucun dossier en retard'
    return f"{n} dossier{'s' if n > 1 else ''} en retard"


DUREE_CACHE = 120  # secondes


def resume(request):
    annee = AnneeAcademique.courante()
    frais = cache.get_or_set(f'lanceur:finance:{annee.pk if annee else 0}', lambda: indicateurs_frais(annee), DUREE_CACHE)
    if frais['taux_recouvrement'] is None:
        return entree('finance', unite='%', libelle='des frais encaissés', detail='Aucun frais attendu')
    retards = frais['dossiers_en_retard']
    return entree('finance', valeur=frais['taux_recouvrement'], unite='%', libelle='des frais encaissés',
                  detail=_retards(retards), ton='alerte' if retards else 'normal')
