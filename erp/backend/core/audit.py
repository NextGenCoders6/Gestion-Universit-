import ipaddress

from rest_framework.settings import api_settings

from core.models import JournalAudit


def _ip_valide(valeur):
    try:
        return str(ipaddress.ip_address((valeur or '').strip()))
    except ValueError:
        return None


def adresse_ip(request):
    """Adresse du client, avec la même règle que la limitation des connexions.

    X-Forwarded-For n'est lu que si des proxys sont déclarés (NUM_PROXIES) : le
    proxy ajoute l'adresse réelle à la fin, les premières valeurs sont falsifiables.
    """
    directe = _ip_valide(request.META.get('REMOTE_ADDR'))
    nb_proxys = api_settings.NUM_PROXIES or 0
    transmise = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if nb_proxys and transmise:
        adresses = [a.strip() for a in transmise.split(',') if a.strip()]
        if adresses:
            return _ip_valide(adresses[-min(nb_proxys, len(adresses))]) or directe
    return directe


def journaliser(request, module, action, description=''):
    user = getattr(request, 'user', None)
    return JournalAudit.objects.create(
        utilisateur=user if user is not None and user.is_authenticated else None,
        module=module,
        action=action,
        description=description,
        adresse_ip=adresse_ip(request),
    )
