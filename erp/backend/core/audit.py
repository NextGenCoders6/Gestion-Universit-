from core.models import JournalAudit


def adresse_ip(request):
    transmise = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if transmise:
        return transmise.split(',')[0].strip() or None
    return request.META.get('REMOTE_ADDR') or None


def journaliser(request, module, action, description=''):
    user = getattr(request, 'user', None)
    return JournalAudit.objects.create(
        utilisateur=user if user is not None and user.is_authenticated else None,
        module=module,
        action=action,
        description=description,
        adresse_ip=adresse_ip(request),
    )
