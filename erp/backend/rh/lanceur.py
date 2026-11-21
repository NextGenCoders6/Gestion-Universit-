"""Résumé RH du launchpad : contrats arrivant à échéance sous 30 jours, vacations à confirmer."""
from core.lanceur import entree
from rh.contrats import contrats_a_echeance


def _vacations(n):
    if n == 0:
        return 'Aucune vacation à confirmer'
    return f"{n} vacation{'s' if n > 1 else ''} à confirmer"


def resume(request):
    from rh.views import _Requete, affectations_de_vacataires, lignes_vacations
    echeances = contrats_a_echeance(30).count()
    a_confirmer = len(lignes_vacations(_Requete(request, 'a_confirmer'), affectations_de_vacataires(request)))
    return entree('rh', valeur=echeances, libelle='contrats à échéance', detail=_vacations(a_confirmer),
                  ton='alerte' if echeances else 'normal')
