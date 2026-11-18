"""Fiche personne unique et rôles rattachés (étudiant, enseignant, employé).

Une personne peut cumuler plusieurs rôles. Chaque module de l'ERP s'appuie sur
ces fiches au lieu de garder sa propre copie.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction

from core.validateurs import nom_validator, valider_date_naissance

from .referentiel import GENRE, AnneeAcademique, Departement, Faculte, ModeleValide


def chemin_photo(instance, nom_fichier):
    extension = nom_fichier.rsplit('.', 1)[-1].lower() if '.' in nom_fichier else 'jpg'
    return f'photos/personne_{instance.pk or "nouveau"}.{extension}'


class Personne(ModeleValide):
    STATUT_CHOICES = [('actif', 'Actif'), ('suspendu', 'Suspendu')]

    nom = models.CharField(max_length=100, validators=[nom_validator])
    prenom = models.CharField(max_length=100, validators=[nom_validator])
    genre = models.CharField(max_length=1, choices=GENRE)
    date_naissance = models.DateField(null=True, blank=True, validators=[valider_date_naissance])
    lieu_naissance = models.CharField(max_length=100, blank=True)
    nationalite = models.CharField(max_length=60, default='Congolaise', blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    adresse = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(upload_to=chemin_photo, max_length=255, null=True, blank=True)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='actif')
    motif_suspension = models.TextField(blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='personne'
    )

    class Meta:
        ordering = ['nom', 'prenom']

    def __str__(self):
        return self.nom_complet

    @property
    def nom_complet(self):
        return f'{self.nom.upper()} {self.prenom}'

    @property
    def est_suspendue(self):
        return self.statut == 'suspendu'

    def clean(self):
        if self.statut == 'suspendu' and not (self.motif_suspension or '').strip():
            raise ValidationError({'motif_suspension': 'Le motif de suspension est obligatoire.'})

    def save(self, *args, **kwargs):
        if not self.email:
            self.email = None
        if self.statut == 'actif':
            self.motif_suspension = ''
        super().save(*args, **kwargs)


TENTATIVES_MATRICULE = 5


def _suffixe_max(matricules):
    maxi = 0
    for m in matricules:
        fin = m[-5:]
        if fin.isdigit():
            maxi = max(maxi, int(fin))
    return maxi


def _prochain_numero(modele, prefixe):
    """Numéro suivant pour « {prefixe}-{n:05d} » ; un numéro libéré n'est jamais repris."""
    existants = modele.objects.filter(matricule__startswith=f'{prefixe}-').values_list('matricule', flat=True)
    return f'{prefixe}-{_suffixe_max(existants) + 1:05d}'


def _lettres(texte, longueur):
    return texte.upper().replace(' ', '').replace('-', '')[:longueur].ljust(longueur, 'X')


def generer_matricule_etudiant(personne, annee):
    """UCCB{AA}{NOM3}{PR2}{n:05d} ; n suit une séquence unique pour tous les étudiants."""
    base = f'UCCB{annee.libelle[2:4]}{_lettres(personne.nom, 3)}{_lettres(personne.prenom, 2)}'
    numero = _suffixe_max(Etudiant.objects.values_list('matricule', flat=True)) + 1
    return f'{base}{numero:05d}'


class MatriculeAutoMixin:
    """Attribue le matricule à la création et réessaie si un autre enregistrement
    simultané a pris le même numéro (contrôle d'unicité ou contrainte en base)."""

    def generer_matricule(self):
        raise NotImplementedError

    def save(self, *args, **kwargs):
        if self.matricule:
            return super().save(*args, **kwargs)
        for tentative in range(TENTATIVES_MATRICULE):
            self.matricule = self.generer_matricule()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except ValidationError as exc:
                if 'matricule' not in getattr(exc, 'error_dict', {}) or tentative == TENTATIVES_MATRICULE - 1:
                    self.matricule = ''
                    raise
            except IntegrityError:
                if tentative == TENTATIVES_MATRICULE - 1:
                    self.matricule = ''
                    raise
            self.matricule = ''
        return None


class Etudiant(MatriculeAutoMixin, ModeleValide):
    STATUT_CHOICES = [
        ('actif', 'Actif — étudiant en cours'),
        ('diplome', 'Diplômé — a terminé son cycle'),
        ('abandonne', 'Abandonné — a quitté sans terminer'),
    ]

    personne = models.OneToOneField(Personne, on_delete=models.CASCADE, primary_key=True, related_name='etudiant')
    matricule = models.CharField(max_length=35, unique=True, editable=False, blank=True)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='actif')
    annee_entree = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT, related_name='etudiants_entres')

    class Meta:
        verbose_name = 'Étudiant'
        ordering = ['personne__nom', 'personne__prenom']

    def __str__(self):
        return f'{self.matricule} — {self.personne}'

    def generer_matricule(self):
        return generer_matricule_etudiant(self.personne, self.annee_entree)


class Enseignant(MatriculeAutoMixin, ModeleValide):
    GRADE_CHOICES = [('', '—'), ('Ingénieur', 'Ingénieur'), ('Docteur', 'Docteur'), ('Professeur', 'Professeur')]

    personne = models.OneToOneField(Personne, on_delete=models.CASCADE, primary_key=True, related_name='enseignant')
    matricule = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    grade = models.CharField(max_length=20, choices=GRADE_CHOICES, blank=True)
    departement = models.ForeignKey(Departement, on_delete=models.PROTECT, related_name='enseignants')

    class Meta:
        ordering = ['personne__nom', 'personne__prenom']

    def __str__(self):
        return f'{self.matricule} — {self.personne}'

    def generer_matricule(self):
        return _prochain_numero(Enseignant, 'UCCB-ENS')


class Employe(MatriculeAutoMixin, ModeleValide):
    FONCTION_CHOICES = [
        ('menage', 'Agent de ménage'),
        ('gardien', 'Gardien / Agent de sécurité'),
        ('cuisinier', 'Cuisinier'),
        ('chauffeur', 'Chauffeur'),
        ('technicien', 'Technicien de maintenance'),
        ('autre', 'Autre'),
    ]

    personne = models.OneToOneField(Personne, on_delete=models.CASCADE, primary_key=True, related_name='employe')
    matricule = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    fonction = models.CharField(max_length=20, choices=FONCTION_CHOICES)
    fonction_autre = models.CharField(max_length=100, blank=True)
    lieu_travail = models.CharField(max_length=100, blank=True)
    faculte_rattachement = models.ForeignKey(
        Faculte, on_delete=models.SET_NULL, null=True, blank=True, related_name='employes'
    )

    class Meta:
        verbose_name = 'Employé'
        ordering = ['personne__nom', 'personne__prenom']

    def __str__(self):
        return f'{self.matricule} — {self.personne}'

    @property
    def fonction_libelle(self):
        return self.fonction_autre if self.fonction == 'autre' else self.get_fonction_display()

    def clean(self):
        if self.fonction == 'autre' and not (self.fonction_autre or '').strip():
            raise ValidationError({'fonction_autre': 'Précisez la fonction.'})

    def generer_matricule(self):
        return _prochain_numero(Employe, 'UCCB-PERS')
