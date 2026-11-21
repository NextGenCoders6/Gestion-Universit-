"""Résumé Logistique du launchpad : bus en service et alertes (chauffeur sans contrat en cours)."""
from django.utils import timezone

from core.lanceur import entree
from logistique import affectations as service
from logistique.models import Bus


def _alertes(n):
    if n == 0:
        return 'Aucune alerte'
    return f"{n} alerte{'s' if n > 1 else ''}"


def resume(request):
    alertes = len(service.alertes(timezone.localdate()))
    return entree('logistique', valeur=Bus.objects.filter(statut='actif').count(), libelle='bus en service',
                  detail=_alertes(alertes), ton='alerte' if alertes else 'normal')
