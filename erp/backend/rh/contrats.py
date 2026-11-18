"""Règles sur les contrats : contrat en cours, échéances, fin anticipée."""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from rh.models import Contrat


def q_en_cours(jour, prefixe=''):
    return (Q(**{f'{prefixe}date_debut__lte': jour})
            & (Q(**{f'{prefixe}date_fin__isnull': True}) | Q(**{f'{prefixe}date_fin__gte': jour})))


def contrat_en_cours(personne, jour=None, type=None):
    """Contrat de la personne en vigueur à `jour` (aujourd'hui par défaut), ou None."""
    qs = Contrat.objects.filter(q_en_cours(jour or timezone.localdate()), personne=personne)
    if type:
        qs = qs.filter(type=type)
    return qs.first()


def contrats_a_echeance(jours=30, jour=None):
    """Contrats en cours qui se terminent dans les `jours` prochains jours."""
    jour = jour or timezone.localdate()
    # Un contrat déjà suivi d'un autre (renouvelé) n'est plus une échéance à traiter.
    suivant = Contrat.objects.filter(personne_id=OuterRef('personne_id'), date_debut__gt=OuterRef('date_fin'))
    return (Contrat.objects.filter(date_debut__lte=jour, date_fin__gte=jour, date_fin__lte=jour + timedelta(days=jours))
            .exclude(Exists(suivant)).select_related('personne').order_by('date_fin'))


def terminer(contrat, date_fin):
    """Fin anticipée (ou fixée) d'un contrat."""
    if date_fin < contrat.date_debut:
        raise ValidationError({'date_fin': 'La date de fin précède la date de début du contrat.'})
    contrat.date_fin = date_fin
    contrat.save()
    return contrat
