"""Launchpad : un chiffre résumé par module, pour les tuiles de l'écran d'accueil.

Chaque app enregistre dans son AppConfig.ready() une fonction `resume(request) -> dict`
(construite avec `entree`), comme pour core.droits.ROLES_CONTEXTUELS. Le résumé est
calculé dans le périmètre de l'utilisateur de la requête.
"""
import logging

from django.contrib.auth import get_user_model

from core.droits import modules_accessibles

logger = logging.getLogger(__name__)

RESUMES = {}


def enregistrer(code, fonction):
    RESUMES[code] = fonction


def entree(module, valeur=None, unite='', libelle='', detail='', ton='normal'):
    return {'module': module, 'valeur': valeur, 'unite': unite, 'libelle': libelle, 'detail': detail, 'ton': ton}


def resumes_pour(request):
    """Résumés des modules accessibles ; un résumé en erreur donne une entrée sans chiffre."""
    resultat = []
    for module in modules_accessibles(request.user):
        code = module['code']
        fonction = RESUMES.get(code)
        if fonction is None:
            continue
        try:
            resultat.append(fonction(request))
        except Exception:
            logger.exception('Résumé du launchpad en erreur pour le module %s', code)
            resultat.append(entree(code))
    return resultat


def resume_parametres(request):
    from core.models import AnneeAcademique
    annee = AnneeAcademique.courante()
    return entree(
        'parametres',
        valeur=get_user_model().objects.filter(is_active=True).count(),
        libelle='comptes actifs',
        detail=f'Année en cours : {annee.libelle}' if annee else 'Aucune année en cours',
        ton='normal' if annee else 'alerte',
    )
