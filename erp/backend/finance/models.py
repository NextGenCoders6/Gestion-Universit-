"""Finance : grille de tarifs, dossiers de frais et leur échéancier mensuel."""
import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import AnneeAcademique, Parcours
from core.models.referentiel import ModeleValide

MOIS = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


def valider_mois(valeur):
    if not MOIS.match(valeur or ''):
        raise ValidationError('Mois invalide (AAAA-MM attendu).')


class Tarif(ModeleValide):
    """Frais de l'année pour un niveau (L1…M2) et leur modalité de paiement mensuelle."""

    annee = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT, related_name='tarifs')
    parcours = models.ForeignKey(Parcours, on_delete=models.PROTECT, related_name='tarifs')
    montant = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    nombre_mensualites = models.PositiveSmallIntegerField(default=10, validators=[
        MinValueValidator(1, 'Au moins une mensualité.'), MaxValueValidator(12, 'Au plus 12 mensualités.')])
    premier_mois = models.CharField(max_length=7, blank=True, validators=[valider_mois],
                                    help_text='Premier mois couvert (AAAA-MM) ; octobre de l’année par défaut.')
    jour_echeance = models.PositiveSmallIntegerField(default=5, validators=[
        MinValueValidator(1, 'Jour entre 1 et 28.'), MaxValueValidator(28, 'Jour entre 1 et 28.')],
        help_text='Jour du mois suivant où la mensualité du mois est due.')

    class Meta:
        ordering = ['-annee__date_debut', 'parcours__type_parcours', 'parcours__niveau']
        constraints = [models.UniqueConstraint(fields=['annee', 'parcours'], name='tarif_unique')]

    def __str__(self):
        return f'{self.parcours.code} {self.annee.libelle} : {self.montant}'

    def clean(self):
        if self.parcours_id and self.parcours.type_parcours not in ('Licence', 'Master'):
            raise ValidationError({'parcours': 'Les tarifs concernent les niveaux L1 à M2.'})
        if not self.premier_mois and self.annee_id:
            self.premier_mois = f'{self.annee.date_debut.year}-10'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from finance.frais import appliquer_tarif
        appliquer_tarif(self)


class FraisScolarite(models.Model):
    """Dossier de frais d'une inscription (un par étudiant et par année)."""

    inscription = models.OneToOneField('scolarite.Inscription', on_delete=models.PROTECT, related_name='frais')
    montant_du = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_ajuste = models.BooleanField(default=False, help_text='Montant fixé à la main : le tarif ne le change plus.')
    echeancier_adapte = models.BooleanField(default=False, help_text='Échéancier adapté à la main.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dossier de frais'
        verbose_name_plural = 'Dossiers de frais'
        ordering = ['inscription__etudiant__personne__nom', 'inscription__etudiant__personne__prenom']

    def __str__(self):
        return f'Frais {self.inscription} : {self.montant_paye}/{self.montant_du}'

    @property
    def statut(self):
        if self.montant_paye <= 0:
            return 'non_paye'
        return 'paye' if self.montant_paye >= self.montant_du else 'partiel'

    @property
    def reste(self):
        return max(Decimal('0'), self.montant_du - self.montant_paye)

    @property
    def trop_percu(self):
        return max(Decimal('0'), self.montant_paye - self.montant_du)


class EcheanceFrais(models.Model):
    dossier = models.ForeignKey(FraisScolarite, on_delete=models.CASCADE, related_name='echeances')
    numero = models.PositiveSmallIntegerField()
    mois = models.CharField(max_length=7, validators=[valider_mois])
    date_limite = models.DateField()
    montant = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['dossier', 'numero']
        constraints = [models.UniqueConstraint(fields=['dossier', 'numero'], name='echeance_unique')]

    def __str__(self):
        return f'{self.dossier} — {self.mois} ({self.montant}, avant le {self.date_limite})'


MODES_PAIEMENT = [('especes', 'Espèces'), ('mobile_money', 'Mobile Money'), ('virement', 'Virement bancaire'),
                  ('cheque', 'Chèque')]


class Compteur(models.Model):
    """Numérotation sans trou des opérations, par année (verrouillée à chaque attribution)."""

    cle = models.CharField(max_length=30, unique=True)
    valeur = models.PositiveIntegerField(default=0)


class Operation(models.Model):
    """Ligne du journal (reprise de Transaction) : jamais supprimée, corrigée par contre-écriture."""

    CATEGORIES = [('frais', 'Frais de scolarité'), ('salaire', 'Salaire'), ('vacation', 'Vacation'),
                  ('transport', 'Transport'), ('manuelle', 'Opération manuelle'), ('annulation', 'Annulation')]

    numero = models.CharField(max_length=20, unique=True)
    date = models.DateField()
    libelle = models.CharField(max_length=255)
    montant = models.DecimalField(max_digits=14, decimal_places=2, help_text='+ recette, − dépense')
    categorie = models.CharField(max_length=12, choices=CATEGORIES)
    annule = models.OneToOneField('self', on_delete=models.PROTECT, null=True, blank=True, related_name='annulation',
                                  help_text='Opération que celle-ci annule (contre-écriture).')
    par = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-numero']

    def __str__(self):
        return f'{self.numero} {self.libelle} {self.montant}'


class PaiementEtudiant(models.Model):
    dossier = models.ForeignKey(FraisScolarite, on_delete=models.PROTECT, related_name='paiements')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    mode = models.CharField(max_length=15, choices=MODES_PAIEMENT)
    date = models.DateField()
    reference = models.CharField(max_length=60, blank=True)
    operation = models.OneToOneField(Operation, on_delete=models.PROTECT, related_name='paiement_etudiant')
    annule = models.BooleanField(default=False)
    motif_annulation = models.CharField(max_length=255, blank=True)
    par = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-pk']


class Paie(models.Model):
    """Ligne de paie : salaire mensuel d'un contrat permanent, ou vacation confirmée par la faculté."""

    ORIGINES = [('salaire', 'Salaire'), ('vacation', 'Vacation')]

    origine = models.CharField(max_length=10, choices=ORIGINES)
    personne = models.ForeignKey('core.Personne', on_delete=models.PROTECT, related_name='paies')
    contrat = models.ForeignKey('rh.Contrat', on_delete=models.PROTECT, related_name='paies')
    mois = models.CharField(max_length=7, null=True, blank=True, validators=[valider_mois],
                            help_text='AAAA-MM pour un salaire ; vide pour une vacation.')
    vacation = models.OneToOneField('rh.Vacation', on_delete=models.CASCADE, null=True, blank=True, related_name='paie')
    montant_du = models.DecimalField(max_digits=12, decimal_places=2)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_ajuste = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-mois', 'personne__nom', 'personne__prenom']
        # Les NULL (vacations) sont distincts dans un index unique : seul un salaire par contrat et par mois.
        constraints = [models.UniqueConstraint(fields=['contrat', 'mois'], name='salaire_unique_par_mois')]

    def __str__(self):
        quoi = f'Salaire {self.mois}' if self.origine == 'salaire' else 'Vacation'
        return f'{quoi} — {self.personne} : {self.montant_paye}/{self.montant_du}'

    @property
    def statut(self):
        if self.montant_paye <= 0:
            return 'en_attente'
        return 'paye' if self.montant_paye >= self.montant_du else 'partiel'

    @property
    def reste(self):
        return max(Decimal('0'), self.montant_du - self.montant_paye)


class PaiementPaie(models.Model):
    # CASCADE : une ligne de paie de vacation retirée emporte ses paiements annulés ; le journal, lui, reste.
    paie = models.ForeignKey(Paie, on_delete=models.CASCADE, related_name='paiements')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    mode = models.CharField(max_length=15, choices=MODES_PAIEMENT)
    date = models.DateField()
    reference = models.CharField(max_length=60, blank=True)
    operation = models.OneToOneField(Operation, on_delete=models.PROTECT, related_name='paiement_paie')
    annule = models.BooleanField(default=False)
    motif_annulation = models.CharField(max_length=255, blank=True)
    par = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-pk']


class DepenseTransport(models.Model):
    TYPES = [('carburant', 'Carburant'), ('entretien', 'Entretien'), ('reparation', 'Réparation')]

    bus = models.ForeignKey('logistique.Bus', on_delete=models.PROTECT, related_name='depenses')
    type = models.CharField(max_length=12, choices=TYPES)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    operation = models.OneToOneField(Operation, on_delete=models.PROTECT, related_name='depense_transport')
    annule = models.BooleanField(default=False)
    motif_annulation = models.CharField(max_length=255, blank=True)
    par = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dépense de transport'
        ordering = ['-date', '-pk']
