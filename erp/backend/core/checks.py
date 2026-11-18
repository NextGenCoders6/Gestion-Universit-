from django.conf import settings
from django.core.checks import Error, register

CLE_DE_DEVELOPPEMENT = 'cle-de-developpement-a-remplacer'


@register()
def verifier_cle_secrete(app_configs, **kwargs):
    """Hors DEBUG, la clé de développement publique permettrait de forger des jetons."""
    if not settings.DEBUG and settings.SECRET_KEY == CLE_DE_DEVELOPPEMENT:
        return [Error(
            'SECRET_KEY vaut la clé de développement publique alors que DEBUG=False.',
            hint='Définissez SECRET_KEY dans le fichier .env (valeur longue et aléatoire).',
            id='core.E001',
        )]
    return []
