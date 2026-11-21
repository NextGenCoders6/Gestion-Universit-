"""Résumé Finance du launchpad : part des frais de l'année en cours déjà encaissée."""
from core.lanceur import entree
from core.models import AnneeAcademique
from finance.tableau import indicateurs_frais


def _retards(n):
    if n == 0:
        return 'Aucun dossier en retard'
    return f"{n} dossier{'s' if n > 1 else ''} en retard"


def resume(request):
    frais = indicateurs_frais(AnneeAcademique.courante())
    if frais['taux_recouvrement'] is None:
        return entree('finance', unite='%', libelle='des frais encaissés', detail='Aucun frais attendu')
    retards = frais['dossiers_en_retard']
    return entree('finance', valeur=frais['taux_recouvrement'], unite='%', libelle='des frais encaissés',
                  detail=_retards(retards), ton='alerte' if retards else 'normal')
