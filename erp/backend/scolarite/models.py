"""Scolarité : inscriptions annuelles, notes par EC, résultats de semestre, documents émis."""
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import SEMESTRES, AnneeAcademique, Classe, ElementConstitutif, Etudiant
from core.models.referentiel import ModeleValide

BORNES_NOTE = [
    MinValueValidator(0, message='Une note est comprise entre 0 et 20.'),
    MaxValueValidator(20, message='Une note est comprise entre 0 et 20.'),
]


def champ_note(nom):
    return models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True,
                               validators=BORNES_NOTE, verbose_name=nom)


class Inscription(ModeleValide):
    """Inscription annuelle d'un étudiant dans une classe (couvre les deux semestres du niveau)."""

    TYPE_CHOICES = [('premiere', 'Première inscription'), ('reinscription', 'Réinscription')]
    STATUT_CHOICES = [('active', 'Active'), ('terminee', 'Terminée'), ('abandonnee', 'Abandonnée')]

    etudiant = models.ForeignKey(Etudiant, on_delete=models.PROTECT, related_name='inscriptions')
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, related_name='inscriptions')
    # Recopiée de la classe : porte la contrainte « une inscription par année ».
    annee = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT, related_name='inscriptions',
                              editable=False)
    type = models.CharField(max_length=15, choices=TYPE_CHOICES, default='premiere')
    statut = models.CharField(max_length=12, choices=STATUT_CHOICES, default='active')
    date_inscription = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-annee__date_debut', 'etudiant__personne__nom', 'etudiant__personne__prenom']
        constraints = [models.UniqueConstraint(fields=['etudiant', 'annee'], name='inscription_annuelle_unique')]

    def __str__(self):
        return f'{self.etudiant.matricule} — {self.classe}'

    def clean(self):
        if not self.classe_id:
            return
        self.annee_id = self.classe.annee_id
        ancienne = None if self._state.adding else Inscription.objects.filter(pk=self.pk).first()
        if (ancienne is None or ancienne.classe_id != self.classe_id) and self.classe.annee.statut == 'archivee':
            raise ValidationError({'classe': "L'année de cette classe est archivée : aucune inscription possible."})
        if self.etudiant_id and Inscription.objects.filter(
                etudiant_id=self.etudiant_id, annee_id=self.annee_id).exclude(pk=self.pk).exists():
            raise ValidationError({'classe': f"L'étudiant est déjà inscrit pour l'année {self.classe.annee.libelle}."})

    def validate_constraints(self, exclude=None):
        # Contrôlée dans clean() avec un message clair.
        pass


class Note(ModeleValide):
    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name='notes')
    ec = models.ForeignKey(ElementConstitutif, on_delete=models.PROTECT, related_name='notes')
    note_devoir = champ_note('Devoir')
    note_session = champ_note('Session')
    note_sr = champ_note('Rattrapage (SR)')
    est_absent = models.BooleanField(default=False)
    moyenne = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, editable=False)

    class Meta:
        ordering = ['inscription', 'ec__ue__semestre', 'ec__ue__code', 'ec__code']
        constraints = [models.UniqueConstraint(fields=['inscription', 'ec'], name='note_unique')]

    def __str__(self):
        return f'{self.inscription.etudiant.matricule} | {self.ec.code} → {self.moyenne}'

    def calculer(self):
        """Moyenne de l'EC (règles de l'ancienne scolarité) ; None tant qu'elle n'est pas saisie."""
        if self.est_absent:
            return 0.0
        if self.note_devoir is None or self.note_session is None:
            return None
        d, s = float(self.note_devoir), float(self.note_session)
        normale = (d + s) / 2
        if self.note_sr is not None:
            return round(max(normale, (d + 2 * float(self.note_sr)) / 3), 2)
        return round(normale, 2)

    @property
    def saisie(self):
        return self.moyenne is not None

    def clean(self):
        if self.note_sr is not None and self.note_session is None and not self.est_absent:
            raise ValidationError({'note_sr': 'Une note de rattrapage suppose une note de session.'})

    def save(self, *args, **kwargs):
        valeur = self.calculer()
        self.moyenne = None if valeur is None else Decimal(str(valeur))
        super().save(*args, **kwargs)


class ResultatSemestre(ModeleValide):
    DECISION_CHOICES = [('ADMIS', 'Admis'), ('AJOURNÉ', 'Ajourné')]

    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name='resultats')
    semestre = models.CharField(max_length=3, choices=SEMESTRES)
    moyenne = models.DecimalField(max_digits=4, decimal_places=2)
    credits_obtenus = models.PositiveSmallIntegerField(default=0)
    credits_totaux = models.PositiveSmallIntegerField(default=0)
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    mention = models.CharField(max_length=12, default='NÉANT')
    rang = models.PositiveSmallIntegerField(null=True, blank=True)
    delibere_le = models.DateTimeField(null=True, blank=True)
    delibere_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='+')

    class Meta:
        verbose_name = 'Résultat de semestre'
        verbose_name_plural = 'Résultats de semestre'
        ordering = ['inscription', 'semestre']
        constraints = [models.UniqueConstraint(fields=['inscription', 'semestre'], name='resultat_unique')]

    def __str__(self):
        return f'{self.inscription.etudiant.matricule} | {self.semestre} | {self.decision} ({self.moyenne})'

    def clean(self):
        if self.inscription_id and self.semestre and self.semestre not in self.inscription.classe.semestres:
            raise ValidationError({'semestre': "Ce semestre n'appartient pas au niveau de la classe."})


def nouveau_jeton():
    return secrets.token_urlsafe(24)  # 32 caractères


class DocumentEmis(models.Model):
    """Trace d'un document officiel émis ; son jeton est encodé dans le QR code."""

    TYPE_CHOICES = [('attestation', 'Attestation de fréquentation'), ('releve', 'Relevé de notes')]

    jeton = models.CharField(max_length=32, unique=True, default=nouveau_jeton, editable=False)
    type = models.CharField(max_length=12, choices=TYPE_CHOICES)
    inscription = models.ForeignKey(Inscription, on_delete=models.PROTECT, related_name='documents')
    semestre = models.CharField(max_length=3, choices=SEMESTRES, blank=True)
    decision = models.CharField(max_length=10, blank=True)
    emis_le = models.DateTimeField(auto_now_add=True)
    emis_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='+')

    class Meta:
        verbose_name = 'Document émis'
        verbose_name_plural = 'Documents émis'
        ordering = ['-emis_le']

    def __str__(self):
        return f'{self.get_type_display()} — {self.inscription.etudiant.matricule} ({self.jeton})'
