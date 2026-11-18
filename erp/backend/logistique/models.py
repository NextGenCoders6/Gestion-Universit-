"""Logistique : bus, trajets et affectations des chauffeurs."""
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from core.models import Employe
from core.models.referentiel import ModeleValide


class Bus(ModeleValide):
    STATUTS = [('actif', 'Actif'), ('maintenance', 'Maintenance'), ('hors_service', 'Hors service')]

    numero = models.CharField(max_length=20, unique=True)
    plaque = models.CharField(max_length=20, unique=True)
    capacite = models.PositiveIntegerField(validators=[MinValueValidator(1, 'La capacité est d’au moins 1 place.')])
    statut = models.CharField(max_length=15, choices=STATUTS, default='actif')

    class Meta:
        verbose_name_plural = 'Bus'
        ordering = ['numero']

    def __str__(self):
        return f'Bus {self.numero} ({self.plaque})'


class Trajet(ModeleValide):
    nom = models.CharField(max_length=100)
    depart = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    heure_depart = models.TimeField()
    heure_arrivee = models.TimeField()

    class Meta:
        ordering = ['heure_depart', 'nom']

    def __str__(self):
        return f'{self.nom} : {self.depart} → {self.destination}'

    def clean(self):
        if self.heure_depart and self.heure_arrivee and self.heure_arrivee <= self.heure_depart:
            raise ValidationError({'heure_arrivee': "L'heure d'arrivée doit suivre l'heure de départ."})


class AffectationTransport(ModeleValide):
    """Un chauffeur conduit un bus sur un trajet pendant une période (une seule active par bus et par chauffeur)."""

    bus = models.ForeignKey(Bus, on_delete=models.PROTECT, related_name='affectations')
    chauffeur = models.ForeignKey(Employe, on_delete=models.PROTECT, related_name='affectations_transport')
    trajet = models.ForeignKey(Trajet, on_delete=models.PROTECT, related_name='affectations')
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Affectation de transport'
        ordering = ['-date_debut', 'bus__numero']

    def __str__(self):
        return f'{self.chauffeur} — {self.bus} — {self.trajet.nom}'

    def est_active(self, jour):
        return self.date_debut <= jour and (self.date_fin is None or self.date_fin >= jour)

    def _chevauchements(self):
        qs = AffectationTransport.objects.exclude(pk=self.pk).filter(
            Q(date_fin__isnull=True) | Q(date_fin__gte=self.date_debut))
        return qs.filter(date_debut__lte=self.date_fin) if self.date_fin else qs

    def clean(self):
        if not (self.bus_id and self.chauffeur_id and self.date_debut):
            return
        erreurs = {}
        if self.date_fin and self.date_fin < self.date_debut:
            erreurs['date_fin'] = 'La date de fin précède la date de début.'
        if self.chauffeur.fonction != 'chauffeur':
            erreurs['chauffeur'] = "Cet employé n'est pas chauffeur."
        else:
            from rh.contrats import contrat_en_cours
            if contrat_en_cours(self.chauffeur.personne, self.date_debut) is None:
                erreurs['chauffeur'] = "Ce chauffeur n'a pas de contrat en cours à la date de début."
        if self._state.adding and self.bus.statut != 'actif':
            erreurs['bus'] = f'Ce bus est {self.bus.get_statut_display().lower()} : il ne peut pas être affecté.'
        if erreurs:
            raise ValidationError(erreurs)
        autres = self._chevauchements()
        if autres.filter(bus_id=self.bus_id).exists():
            raise ValidationError({'bus': 'Ce bus a déjà une affectation sur cette période : terminez-la d’abord.'})
        if autres.filter(chauffeur_id=self.chauffeur_id).exists():
            raise ValidationError({'chauffeur': 'Ce chauffeur conduit déjà un bus sur cette période.'})
