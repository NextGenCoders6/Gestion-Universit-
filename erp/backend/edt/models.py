"""Modèles du module Emploi du temps.

Portés de uccb_backend/EDT_app/models.py sur le référentiel du socle :
Module → core.ElementConstitutif (dans une classe donnée), Semestre →
core.Periode, Profil/Enseignant → core.Personne/core.Enseignant.
"""
from datetime import date as date_type, datetime, time as time_type

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum

from core.models import Classe, ElementConstitutif, Enseignant

TYPES_SEANCE = [('CM', 'CM'), ('TD', 'TD'), ('TP', 'TP')]


class AffectationEC(models.Model):
    """Répartition des charges : un enseignant, un EC dans une classe, un volume.

    type_seance vide = affectation générique (tous types). Pour un même
    (EC, classe, enseignant), on ne mélange pas générique et typées. Le
    dépassement du quota de l'EC est signalé, pas bloqué.
    """

    ec = models.ForeignKey(ElementConstitutif, on_delete=models.PROTECT, related_name='affectations')
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, related_name='affectations')
    enseignant = models.ForeignKey(Enseignant, on_delete=models.PROTECT, related_name='affectations')
    type_seance = models.CharField(max_length=5, choices=TYPES_SEANCE, null=True, blank=True,
                                   help_text='Laisser vide pour une affectation générique (tous types).')
    heures_prevues = models.FloatField(
        validators=[MinValueValidator(0, message='Le volume prévu ne peut pas être négatif.')]
    )
    hors_departement = models.BooleanField(
        default=False,
        help_text="Enseignant d'un autre département que celui qui porte l'EC (intervention inter-départements).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Affectation d'enseignement"
        verbose_name_plural = "Affectations d'enseignement"
        ordering = ['classe', 'ec', 'enseignant', 'type_seance']

    def __str__(self):
        return f'{self.enseignant} — {self.ec.code} ({self.classe}) {self.type_seance or "tous types"}'

    def clean(self):
        if not (self.ec_id and self.classe_id and self.enseignant_id):
            return
        from edt.validation import valider_ec_dans_classe
        valider_ec_dans_classe(self.ec, self.classe)
        if not self.hors_departement and self.enseignant.departement_id != self.ec.departement_id:
            raise ValidationError({'enseignant': (
                f"L'enseignant ({self.enseignant.departement}) n'est pas du département qui porte l'EC "
                f"({self.ec.departement}). Cochez « hors département » pour une intervention inter-départements."
            )})
        autres = AffectationEC.objects.filter(
            ec_id=self.ec_id, classe_id=self.classe_id, enseignant_id=self.enseignant_id,
        ).exclude(pk=self.pk)
        if self.type_seance is None:
            if autres.filter(type_seance__isnull=True).exists():
                raise ValidationError('Cet enseignant a déjà une affectation générique sur cet EC dans cette classe. '
                                      "Modifiez-la plutôt que d'en créer une seconde.")
            if autres.filter(type_seance__isnull=False).exists():
                raise ValidationError('Impossible de créer une affectation générique : cet enseignant a déjà des '
                                      'affectations typées (CM/TD/TP) sur cet EC dans cette classe.')
        else:
            if autres.filter(type_seance=self.type_seance).exists():
                raise ValidationError(f'Cet enseignant a déjà une affectation {self.type_seance} sur cet EC dans '
                                      "cette classe. Modifiez-la plutôt que d'en créer une seconde.")
            if autres.filter(type_seance__isnull=True).exists():
                raise ValidationError('Impossible de créer une affectation typée : cet enseignant a déjà une '
                                      'affectation générique sur cet EC dans cette classe.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ── Quotas ───────────────────────────────────────────────────
    def heures_consommees(self, exclure=None):
        from edt import quotas
        return quotas.heures_consommees(self.ec, self.classe, enseignant=self.enseignant,
                                        type_seance=self.type_seance, exclure=exclure)

    def heures_effectuees(self):
        from edt import quotas
        return quotas.heures_effectuees(self.ec, self.classe, enseignant=self.enseignant,
                                        type_seance=self.type_seance)

    def heures_restantes(self, exclure=None):
        return self.heures_prevues - self.heures_consommees(exclure)

    def volume_total_affectations(self):
        autres = AffectationEC.objects.filter(ec_id=self.ec_id, classe_id=self.classe_id).exclude(pk=self.pk)
        return (autres.aggregate(total=Sum('heures_prevues'))['total'] or 0) + (self.heures_prevues or 0)

    def has_volume_warning(self):
        from edt import quotas
        return self.volume_total_affectations() > quotas.heures_max(self.ec)


class Seance(models.Model):
    MIN_HEURE_DEBUT = time_type(9, 0)
    PAUSE_DEBUT = time_type(11, 0)
    PAUSE_FIN = time_type(11, 15)
    HEURE_FIN_MAX = time_type(16, 20)
    MAX_HEURES_JOUR = 6
    HEURES_PAR_CREDIT = 12

    TYPE_CHOICES = TYPES_SEANCE
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('Confirmée', 'Confirmée'),
        ('Annulée', 'Annulée'),
        ('Reportée', 'Reportée'),
    ]

    libelle = models.CharField(max_length=100, blank=True)
    date_seance = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    type_seance = models.CharField(max_length=5, choices=TYPE_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    date_report = models.DateField(null=True, blank=True)
    heure_debut_report = models.TimeField(null=True, blank=True)
    heure_fin_report = models.TimeField(null=True, blank=True)
    ec = models.ForeignKey(ElementConstitutif, on_delete=models.PROTECT, related_name='seances')
    enseignant = models.ForeignKey(Enseignant, on_delete=models.PROTECT, related_name='seances')
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, related_name='seances')
    # Séance jumelle d'un cours mutualisé (même cours, même créneau, autre classe).
    seance_liee = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='seances_associees')

    class Meta:
        verbose_name = 'Séance'
        ordering = ['date_seance', 'heure_debut']
        indexes = [
            models.Index(fields=['enseignant', 'date_seance', 'statut']),
            models.Index(fields=['classe', 'date_seance', 'statut']),
        ]

    def __str__(self):
        return f'{self.ec.code} — {self.classe} — {self.date_seance} {self.heure_debut:%H:%M}'

    @property
    def annee(self):
        return self.classe.annee

    def clean(self):
        from edt import validation as v
        if not (self.ec_id and self.classe_id and self.enseignant_id):
            return
        v.valider_horaires(self.heure_debut, self.heure_fin)
        v.valider_dimanche(self.date_seance)
        v.valider_annee_non_archivee(self.classe.annee)
        v.valider_ec_dans_classe(self.ec, self.classe)
        v.valider_departement(self.enseignant, self.ec, self.classe)
        v.valider_bornes_periode(self.date_seance, self.classe, self.ec)
        if self.statut == 'Reportée':
            v.valider_creneau_report(self)
        v.valider_seance_liee(self)

        jour, debut, fin = self.creneau_effectif()
        exemptes = list(self.seances_associees.values_list('pk', flat=True)) if self.pk else []
        if self.seance_liee_id:
            exemptes.append(self.seance_liee_id)
        v.valider_conflit_enseignant(self.enseignant, jour, debut, fin, self.pk, exemptes)
        v.valider_conflit_classe(self.classe, jour, debut, fin, self.pk)
        v.valider_doublon(self.statut, self.classe, self.ec, self.date_seance, self.heure_debut, self.heure_fin,
                          self.pk)
        if self.statut in ('Confirmée', 'Reportée'):
            duree = v.duree_effective(debut, fin)
            v.valider_volume_ec(self.ec, self.classe, duree, self.pk)
            v.valider_affectation(self.ec, self.classe, self.enseignant, self.type_seance, duree, self.pk)
            v.valider_volume_journalier(self.classe, jour, debut, fin, self.pk)

    def save(self, *args, **kwargs):
        """Valide sous verrou : deux enregistrements simultanés ne passent pas tous les deux les contrôles."""
        from django.db import transaction
        with transaction.atomic():
            filtres = models.Q()
            if self.enseignant_id:
                filtres |= models.Q(enseignant_id=self.enseignant_id)
            if self.classe_id:
                filtres |= models.Q(classe_id=self.classe_id)
            if filtres:
                list(Seance.objects.select_for_update().filter(filtres).exclude(pk=self.pk).values_list('pk', flat=True))
            self.full_clean()
            super().save(*args, **kwargs)

    @staticmethod
    def calculer_duree_effective(heure_debut, heure_fin):
        """Durée en heures, pause de 11:00–11:15 déduite."""
        debut = datetime.combine(date_type.today(), heure_debut)
        fin = datetime.combine(date_type.today(), heure_fin)
        duree = fin - debut
        pause_debut = datetime.combine(date_type.today(), Seance.PAUSE_DEBUT)
        pause_fin = datetime.combine(date_type.today(), Seance.PAUSE_FIN)
        if debut < pause_fin and fin > pause_debut:
            duree -= min(fin, pause_fin) - max(debut, pause_debut)
        return duree.total_seconds() / 3600

    def creneau_effectif(self):
        """(jour, début, fin) réellement occupés : le report s'il est complet, sinon l'original."""
        if self.statut == 'Reportée' and self.heure_debut_report and self.heure_fin_report:
            return self.date_report, self.heure_debut_report, self.heure_fin_report
        return self.date_seance, self.heure_debut, self.heure_fin

    @staticmethod
    def dedupliquer_mutualisees(seances):
        """Ne garde qu'une séance par paire mutualisée de même créneau (la plus petite clé)."""
        seances = list(seances)
        par_pk = {s.pk: s for s in seances}
        resultat = []
        for s in seances:
            partenaire = par_pk.get(s.seance_liee_id) if s.seance_liee_id else None
            if partenaire is not None and s.pk > partenaire.pk and s.creneau_effectif() == partenaire.creneau_effectif():
                continue
            resultat.append(s)
        return resultat
