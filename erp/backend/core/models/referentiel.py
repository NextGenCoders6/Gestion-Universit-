"""Référentiel académique unique, partagé par tous les modules de l'ERP.

Fusion des référentiels de l'ancienne scolarité (Faculté → Portail → Filière,
UE → Matière) et de l'ancien EDT (Faculté → Département → Filière, Parcours,
Classe, Module). Les règles de validation sont reprises de
uccb_backend/EDT_app/models.py et uccb_backend/gestion_eleves/models.py.
"""
import re

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction

GENRE = [('M', 'Masculin'), ('F', 'Féminin')]
SEMESTRES = [(f'S{i}', f'Semestre {i}') for i in range(1, 11)]


class ModeleValide(models.Model):
    """Base : chaque sauvegarde passe par full_clean() (comportement de l'EDT)."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ── Calendrier ───────────────────────────────────────────────────

class AnneeAcademique(ModeleValide):
    STATUT_CHOICES = [('active', 'Active'), ('archivee', 'Archivée')]

    libelle = models.CharField(max_length=9, unique=True)
    date_debut = models.DateField()
    date_fin = models.DateField()
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='active')
    en_cours = models.BooleanField(
        default=False, help_text="Année de travail par défaut. Une seule à la fois."
    )

    class Meta:
        verbose_name = 'Année académique'
        verbose_name_plural = 'Années académiques'
        ordering = ['-libelle']

    def __str__(self):
        return self.libelle

    @classmethod
    def courante(cls):
        return cls.objects.filter(en_cours=True).first()

    def clean(self):
        if not re.match(r'^\d{4}-\d{4}$', self.libelle or ''):
            raise ValidationError({'libelle': 'Le format doit être AAAA-AAAA. Ex : 2026-2027.'})
        debut, fin = (int(x) for x in self.libelle.split('-'))
        if fin != debut + 1:
            raise ValidationError(
                {'libelle': "L'année de fin doit être exactement un an après l'année de début."}
            )
        if self.date_debut and self.date_fin:
            if self.date_debut >= self.date_fin:
                raise ValidationError({'date_fin': 'La date de fin doit être après la date de début.'})
            if self.date_debut.year != debut:
                raise ValidationError({'date_debut': f'La date de début doit être en {debut}.'})
            if self.date_fin.year != fin:
                raise ValidationError({'date_fin': f'La date de fin doit être en {fin}.'})
        if self.en_cours and self.statut == 'archivee':
            raise ValidationError({'en_cours': "Une année archivée ne peut pas être l'année en cours."})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.en_cours:
                AnneeAcademique.objects.exclude(pk=self.pk).filter(en_cours=True).update(en_cours=False)


class Periode(ModeleValide):
    """Une des deux périodes calendaires d'une année (semestres impairs = 1, pairs = 2)."""

    annee = models.ForeignKey(AnneeAcademique, on_delete=models.CASCADE, related_name='periodes')
    numero = models.PositiveSmallIntegerField(choices=[(1, 'Semestre 1'), (2, 'Semestre 2')])
    date_debut = models.DateField()
    date_fin = models.DateField()

    class Meta:
        verbose_name = 'Période'
        ordering = ['annee', 'numero']
        constraints = [models.UniqueConstraint(fields=['annee', 'numero'], name='periode_unique_par_annee')]

    def __str__(self):
        return f'{self.get_numero_display()} {self.annee}'

    def clean(self):
        if not self.annee_id or not self.date_debut or not self.date_fin:
            return
        if self.date_debut < self.annee.date_debut:
            raise ValidationError({
                'date_debut': f"La période ne peut pas commencer avant l'année académique ({self.annee.date_debut})."
            })
        if self.date_fin > self.annee.date_fin:
            raise ValidationError({
                'date_fin': f"La période ne peut pas se terminer après l'année académique ({self.annee.date_fin})."
            })
        if self.date_debut >= self.date_fin:
            raise ValidationError({'date_fin': 'La date de début doit être antérieure à la date de fin.'})


# ── Organisation ─────────────────────────────────────────────────

class Faculte(ModeleValide):
    nom = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text='Ex : FST')
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    genre_doyen = models.CharField(max_length=1, choices=GENRE, default='M')
    nom_doyen = models.CharField(max_length=100, blank=True)
    genre_vice_doyen = models.CharField(max_length=1, choices=GENRE, default='M')
    nom_vice_doyen = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Faculté'
        ordering = ['nom']

    def __str__(self):
        return f'{self.nom} ({self.code})'

    @property
    def titre_doyen(self):
        return 'La Doyenne' if self.genre_doyen == 'F' else 'Le Doyen'

    @property
    def titre_vice_doyen(self):
        return 'La Vice-Doyenne' if self.genre_vice_doyen == 'F' else 'Le Vice-Doyen'

    @property
    def signataire_pv(self):
        """Signataire de la matrice A3 : le doyen ou la doyenne."""
        return self.titre_doyen, (self.nom_doyen or '—')


class Departement(ModeleValide):
    libelle = models.CharField(max_length=100)
    faculte = models.ForeignKey(Faculte, on_delete=models.PROTECT, related_name='departements')
    chef = models.ForeignKey(
        'core.Enseignant', on_delete=models.SET_NULL, null=True, blank=True, related_name='departements_diriges'
    )

    class Meta:
        verbose_name = 'Département'
        ordering = ['faculte', 'libelle']
        constraints = [
            models.UniqueConstraint(fields=['faculte', 'libelle'], name='departement_unique_par_faculte')
        ]

    def __str__(self):
        return f'{self.libelle} ({self.faculte.code})'


class Portail(ModeleValide):
    """Tronc commun de L1 (MIP, BCG, PCG…)."""

    faculte = models.ForeignKey(Faculte, on_delete=models.PROTECT, related_name='portails')
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10, help_text='Ex : MIP')

    class Meta:
        ordering = ['faculte', 'code']
        constraints = [models.UniqueConstraint(fields=['faculte', 'code'], name='portail_unique_par_faculte')]

    def __str__(self):
        return f'{self.code} ({self.faculte.code})'


class Filiere(ModeleValide):
    """Spécialisation à partir de L2, portée par un département."""

    departement = models.ForeignKey(Departement, on_delete=models.PROTECT, related_name='filieres')
    portail = models.ForeignKey(
        Portail, on_delete=models.PROTECT, related_name='filieres', help_text="Portail d'origine (L1)."
    )
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10, help_text='Ex : INFO')
    responsable = models.ForeignKey(
        'core.Enseignant', on_delete=models.SET_NULL, null=True, blank=True, related_name='filieres_responsable'
    )

    class Meta:
        verbose_name = 'Filière'
        ordering = ['departement', 'code']
        constraints = [
            models.UniqueConstraint(fields=['departement', 'code'], name='filiere_unique_par_departement')
        ]

    def __str__(self):
        return f'{self.nom} ({self.code})'

    @property
    def faculte(self):
        return self.departement.faculte

    def clean(self):
        if self.departement_id and self.portail_id and self.portail.faculte_id != self.departement.faculte_id:
            raise ValidationError(
                {'portail': "Le portail d'origine doit appartenir à la même faculté que le département."}
            )


class Parcours(ModeleValide):
    TYPE_CHOICES = [('Licence', 'Licence'), ('Master', 'Master'), ('Doctorat', 'Doctorat')]
    NIVEAUX_MAX = {'Licence': 3, 'Master': 2, 'Doctorat': 3}
    PREFIXES = {'Licence': 'L', 'Master': 'M', 'Doctorat': 'D'}

    type_parcours = models.CharField(max_length=10, choices=TYPE_CHOICES)
    niveau = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['type_parcours', 'niveau']
        constraints = [
            models.UniqueConstraint(fields=['type_parcours', 'niveau'], name='parcours_unique')
        ]

    def __str__(self):
        return self.code

    @property
    def code(self):
        return f'{self.PREFIXES.get(self.type_parcours, "?")}{self.niveau}'

    @property
    def semestres(self):
        """Les deux semestres de cursus couverts par ce niveau (vide pour le Doctorat)."""
        if self.type_parcours == 'Licence':
            rang = self.niveau
        elif self.type_parcours == 'Master':
            rang = 3 + self.niveau
        else:
            return ()
        return (f'S{2 * rang - 1}', f'S{2 * rang}')

    def clean(self):
        if self.niveau is None or not self.type_parcours:
            return
        if self.niveau < 1:
            raise ValidationError({'niveau': 'Le niveau doit être au moins 1.'})
        maxi = self.NIVEAUX_MAX.get(self.type_parcours)
        if maxi and self.niveau > maxi:
            raise ValidationError({'niveau': f'{self.type_parcours} ne peut pas dépasser le niveau {maxi}.'})


class Classe(ModeleValide):
    """Classe annuelle : un niveau (L1…M2) d'une année, sur un portail (L1) ou une filière."""

    annee = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT, related_name='classes')
    parcours = models.ForeignKey(Parcours, on_delete=models.PROTECT, related_name='classes')
    portail = models.ForeignKey(Portail, on_delete=models.PROTECT, null=True, blank=True, related_name='classes')
    filiere = models.ForeignKey(Filiere, on_delete=models.PROTECT, null=True, blank=True, related_name='classes')
    libelle = models.CharField(max_length=120, editable=False)

    class Meta:
        ordering = ['annee', 'parcours', 'libelle']
        constraints = [
            models.UniqueConstraint(
                fields=['annee', 'parcours', 'portail'], condition=models.Q(portail__isnull=False),
                name='classe_unique_portail',
            ),
            models.UniqueConstraint(
                fields=['annee', 'parcours', 'filiere'], condition=models.Q(filiere__isnull=False),
                name='classe_unique_filiere',
            ),
        ]

    def __str__(self):
        return self.libelle

    @property
    def semestres(self):
        return self.parcours.semestres

    @property
    def faculte(self):
        return self.portail.faculte if self.portail_id else self.filiere.faculte

    def clean(self):
        if not self.parcours_id:
            return
        if self.parcours.type_parcours == 'Doctorat':
            raise ValidationError({'parcours': "Le Doctorat n'a pas de classes dans l'ERP."})
        if bool(self.portail_id) == bool(self.filiere_id):
            raise ValidationError('Une classe est rattachée soit à un portail (L1), soit à une filière, pas aux deux.')
        if self.parcours.code == 'L1' and not self.portail_id:
            raise ValidationError({'filiere': 'Une classe de L1 est rattachée à un portail, pas à une filière.'})
        if self.parcours.code != 'L1' and not self.filiere_id:
            raise ValidationError({'portail': "À partir de la L2, une classe est rattachée à une filière."})
        doublons = Classe.objects.filter(
            annee_id=self.annee_id, parcours_id=self.parcours_id,
            portail_id=self.portail_id, filiere_id=self.filiere_id,
        ).exclude(pk=self.pk)
        if self.annee_id and doublons.exists():
            raise ValidationError('Cette classe existe déjà pour cette année.')

    def save(self, *args, **kwargs):
        if self.parcours_id and self.annee_id and (self.portail_id or self.filiere_id):
            rattachement = self.portail if self.portail_id else self.filiere
            self.libelle = f'{self.parcours.code} {rattachement.code} — {self.annee.libelle}'
        super().save(*args, **kwargs)


# ── Enseignements ────────────────────────────────────────────────

class UniteEnseignement(ModeleValide):
    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=150)
    semestre = models.CharField(max_length=3, choices=SEMESTRES)
    portail = models.ForeignKey(Portail, on_delete=models.PROTECT, null=True, blank=True, related_name='ues')
    filiere = models.ForeignKey(Filiere, on_delete=models.PROTECT, null=True, blank=True, related_name='ues')

    class Meta:
        verbose_name = "Unité d'enseignement"
        verbose_name_plural = "Unités d'enseignement"
        ordering = ['semestre', 'code']

    def __str__(self):
        return f'{self.code} — {self.libelle}'

    @property
    def numero_semestre(self):
        return int(self.semestre[1:])

    @property
    def periode_numero(self):
        return 1 if self.numero_semestre % 2 else 2

    @property
    def credits_total(self):
        return sum(e.credits for e in self.ecs.all())

    def clean(self):
        if bool(self.portail_id) == bool(self.filiere_id):
            raise ValidationError("Une UE est rattachée soit à un portail, soit à une filière, pas aux deux.")
        if not self.semestre:
            return
        if self.numero_semestre <= 2 and not self.portail_id:
            raise ValidationError({'filiere': 'Les UE de S1 et S2 sont rattachées à un portail.'})
        if self.numero_semestre > 2 and not self.filiere_id:
            raise ValidationError({'portail': 'À partir du S3, une UE est rattachée à une filière.'})


class ElementConstitutif(ModeleValide):
    """Unité pédagogique unique : on y saisit des notes et on y planifie des séances."""

    ue = models.ForeignKey(UniteEnseignement, on_delete=models.PROTECT, related_name='ecs')
    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=150)
    credits = models.PositiveSmallIntegerField(validators=[
        MinValueValidator(1, message='Un EC doit avoir au moins 1 crédit.'),
        MaxValueValidator(6, message='Les crédits ne peuvent pas dépasser 6.'),
    ])
    heures_cm = models.PositiveIntegerField(default=0)
    heures_td = models.PositiveIntegerField(default=0)
    heures_tp = models.PositiveIntegerField(default=0)
    departement = models.ForeignKey(Departement, on_delete=models.PROTECT, related_name='ecs')
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Élément constitutif'
        verbose_name_plural = 'Éléments constitutifs'
        ordering = ['ue', 'code']

    def __str__(self):
        return f'{self.code} — {self.libelle} ({self.credits} cr.)'

    @property
    def heures_total(self):
        return (self.heures_cm or 0) + (self.heures_td or 0) + (self.heures_tp or 0)

    @property
    def semestre(self):
        return self.ue.semestre


# ── Établissement ────────────────────────────────────────────────

class ParametresEtablissement(ModeleValide):
    nom_secretaire = models.CharField(max_length=200, blank=True)
    genre_secretaire = models.CharField(max_length=1, choices=GENRE, default='M')
    ville_signature = models.CharField(max_length=100, default='Liambou')

    class Meta:
        verbose_name = "Paramètres de l'établissement"
        verbose_name_plural = "Paramètres de l'établissement"

    def __str__(self):
        return "Paramètres de l'établissement"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def titre_secretaire(self):
        return 'La Secrétaire Universitaire' if self.genre_secretaire == 'F' else 'Le Secrétaire Universitaire'
