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


@register()
def verifier_base_url(app_configs, **kwargs):
    """Hors DEBUG, les QR codes des documents officiels pointeraient vers une adresse locale."""
    from django.core.checks import Warning as Avertissement
    base = getattr(settings, 'BASE_URL', '')
    if not settings.DEBUG and any(x in base for x in ('localhost', '127.0.0.1', '[::1]')):
        return [Avertissement(
            f'BASE_URL vaut « {base} » alors que DEBUG=False : les QR codes des documents pointeront vers cette adresse.',
            hint='Définissez BASE_URL dans le fichier .env avec l’adresse publique de l’ERP.',
            id='core.W002',
        )]
    return []
