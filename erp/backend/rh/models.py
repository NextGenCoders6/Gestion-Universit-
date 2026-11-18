"""Ressources humaines : contrats des enseignants et du personnel, vacations."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import Personne
from core.models.referentiel import ModeleValide


class Contrat(ModeleValide):
    TYPE_CHOICES = [('permanent', 'Permanent'), ('vacataire', 'Vacataire')]

    personne = models.ForeignKey(Personne, on_delete=models.PROTECT, related_name='contrats')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True, help_text='Vide : durée indéterminée.')
    salaire_mensuel = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                          validators=[MinValueValidator(0)])
    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       validators=[MinValueValidator(0)])
    rib = models.CharField('RIB', max_length=40, blank=True)
    numero_secu = models.CharField('N° de sécurité sociale', max_length=30, blank=True)
    diplome = models.CharField('Diplôme', max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['personne__nom', 'personne__prenom', '-date_debut']

    def __str__(self):
        fin = self.date_fin.isoformat() if self.date_fin else '…'
        return f'{self.personne} — {self.get_type_display()} {self.date_debut.isoformat()} → {fin}'

    def etat(self, jour=None):
        jour = jour or timezone.localdate()
        if jour < self.date_debut:
            return 'a_venir'
        if self.date_fin and jour > self.date_fin:
            return 'expire'
        return 'en_cours'

    def clean(self):
        erreurs = {}
        p = self.personne if self.personne_id else None
        if p is not None and not (hasattr(p, 'enseignant') or hasattr(p, 'employe')):
            erreurs['personne'] = 'Un contrat concerne un enseignant ou un membre du personnel.'
        if self.type == 'vacataire':
            if p is not None and not hasattr(p, 'enseignant'):
                erreurs['type'] = 'Seul un enseignant peut avoir un contrat de vacataire.'
            if not self.taux_horaire or self.taux_horaire <= 0:
                erreurs['taux_horaire'] = 'Indiquez le taux horaire du vacataire.'
        elif self.type == 'permanent' and (not self.salaire_mensuel or self.salaire_mensuel <= 0):
            erreurs['salaire_mensuel'] = 'Indiquez le salaire mensuel.'
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            erreurs['date_fin'] = 'La date de fin précède la date de début.'
        if erreurs:
            raise ValidationError(erreurs)
        if self.personne_id and self.date_debut:
            # Deux intervalles [d1, f1] et [d2, f2] (f vide = sans fin) se chevauchent si d1 ≤ f2 et d2 ≤ f1.
            autres = Contrat.objects.filter(personne_id=self.personne_id).exclude(pk=self.pk).filter(
                Q(date_fin__isnull=True) | Q(date_fin__gte=self.date_debut))
            if self.date_fin:
                autres = autres.filter(date_debut__lte=self.date_fin)
            autre = autres.first()
            if autre is not None:
                raise ValidationError({'date_debut': f'Ce contrat chevauche un autre contrat de la personne ({autre}).'})


class Vacation(models.Model):
    """Confirmation par la faculté d'une affectation d'un vacataire : heures retenues, taux et montant figés."""

    affectation = models.OneToOneField('edt.AffectationEC', on_delete=models.PROTECT, related_name='vacation')
    contrat = models.ForeignKey(Contrat, on_delete=models.PROTECT, related_name='vacations')
    heures_effectuees = models.DecimalField(max_digits=6, decimal_places=2)
    heures_retenues = models.DecimalField(max_digits=6, decimal_places=2)
    motif = models.CharField(max_length=255, blank=True)
    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    confirmee_le = models.DateTimeField(auto_now_add=True)
    confirmee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='+')

    class Meta:
        ordering = ['-confirmee_le']

    def __str__(self):
        return f'Vacation {self.affectation} — {self.heures_retenues} h × {self.taux_horaire} = {self.montant}'


class HistoriqueVacation(models.Model):
    ACTIONS = [('confirmation', 'Confirmation'), ('retrait', 'Retrait de la confirmation')]

    affectation = models.ForeignKey('edt.AffectationEC', on_delete=models.CASCADE, related_name='historique_vacation')
    action = models.CharField(max_length=12, choices=ACTIONS)
    heures_retenues = models.DecimalField(max_digits=6, decimal_places=2)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    motif = models.CharField(max_length=255, blank=True)
    par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    le = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-le', '-pk']
