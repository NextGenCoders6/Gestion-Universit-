"""Résumé EDT du launchpad : séances publiées de la semaine (lundi → dimanche) et brouillons à venir, dans le périmètre."""
from datetime import timedelta

from django.utils import timezone

from core.lanceur import entree
from edt.models import Seance
from edt.perimetre import classes_autorisees, filtrer_par_classes
from edt.validation import q_jour_effectif


def _brouillons(n):
    if n == 0:
        return 'Aucun brouillon'
    return f'{n} brouillon à publier' if n == 1 else f'{n} brouillons à publier'


def resume(request):
    jour = timezone.localdate()
    lundi = jour - timedelta(days=jour.weekday())
    seances = filtrer_par_classes(Seance.objects.filter(q_jour_effectif(lundi, lundi + timedelta(days=6))),
                                  classes_autorisees(request.user))
    # Brouillons à venir, au-delà de la semaine : ce qui reste à publier.
    brouillons = filtrer_par_classes(Seance.objects.filter(statut='brouillon', date_seance__gte=jour),
                                     classes_autorisees(request.user))
    return entree('edt', valeur=seances.filter(statut__in=['Confirmée', 'Reportée']).count(),
                  libelle='séances cette semaine', detail=_brouillons(brouillons.count()))
