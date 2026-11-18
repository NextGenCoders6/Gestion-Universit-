"""Données de démonstration de l'emploi du temps (après seed_socle ; idempotent)."""
from datetime import date, time, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.management.commands.seed_socle import MOT_DE_PASSE_DEMO
from core.models import (
    AnneeAcademique, Classe, Departement, ElementConstitutif, Enseignant, Filiere, Parcours, Personne, Portail,
    UniteEnseignement,
)
from edt.models import AffectationEC, ReferentClasse, Seance

PREMIER_LUNDI = date(2026, 10, 5)
SEMAINES_CONFIRMEES = 3   # puis une semaine en brouillon
CRENEAUX = {'matin': (time(9, 0), time(11, 0)), 'midi': (time(11, 15), time(13, 15)),
            'aprem': (time(14, 15), time(16, 15))}


class Command(BaseCommand):
    help = "Crée les données de démonstration de l'emploi du temps (après seed_socle)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_edt est refusé quand DEBUG=False (données de démonstration).')
        if not AnneeAcademique.objects.filter(libelle='2026-2027').exists():
            call_command('seed_socle', verbosity=0)
        with transaction.atomic():
            self._programme()
            self._enseignants()
            self._affectations()
            self._seances()
        self.stdout.write(self.style.SUCCESS('Emploi du temps de démonstration prêt (comptes enseignant, referent).'))

    # ── Référentiel complémentaire ───────────────────────────────
    def _programme(self):
        annee = AnneeAcademique.objects.get(libelle='2026-2027')
        info = Departement.objects.get(libelle='Informatique')
        mip, bcg = Portail.objects.get(code='MIP'), Portail.objects.get(code='BCG')
        fil_info = Filiere.objects.get(code='INFO')
        self.l1_mip = Classe.objects.get(annee=annee, parcours__type_parcours='Licence', parcours__niveau=1, portail=mip)
        self.l1_bcg = Classe.objects.get(annee=annee, parcours__type_parcours='Licence', parcours__niveau=1, portail=bcg)
        l2 = Parcours.objects.get(type_parcours='Licence', niveau=2)
        self.l2_info = Classe.objects.get(annee=annee, parcours=l2, filiere=fil_info)
        ue_bcg, _ = UniteEnseignement.objects.get_or_create(
            code='UE-BCG-S1-1', defaults={'libelle': 'Outils informatiques', 'semestre': 'S1', 'portail': bcg})
        ue_s3, _ = UniteEnseignement.objects.get_or_create(
            code='UE-INFO-S3-1', defaults={'libelle': 'Systèmes et données', 'semestre': 'S3', 'filiere': fil_info})
        for code, libelle, credits, ue in (('INFOBCG', 'Initiation à l’algorithmique', 2, ue_bcg),
                                           ('BDD', 'Bases de données', 3, ue_s3),
                                           ('RES', 'Réseaux', 3, ue_s3)):
            ElementConstitutif.objects.get_or_create(code=code, defaults={
                'ue': ue, 'libelle': libelle, 'credits': credits, 'departement': info,
                'heures_cm': credits * 6, 'heures_td': credits * 4, 'heures_tp': credits * 2})
        self.ec = {c: ElementConstitutif.objects.get(code=c) for c in ('ALGO1', 'PROG1', 'ARCHI1', 'INFOBCG', 'BDD', 'RES')}

    def _enseignant(self, nom, prenom, genre, username=None):
        info = Departement.objects.get(libelle='Informatique')
        personne, _ = Personne.objects.get_or_create(nom=nom, prenom=prenom, defaults={'genre': genre})
        ens, _ = Enseignant.objects.get_or_create(personne=personne, defaults={'departement': info, 'grade': 'Docteur'})
        if username and personne.user_id is None:
            user = User.objects.filter(username=username).first() or User.objects.create_user(
                username, password=MOT_DE_PASSE_DEMO)
            personne.user = user
            personne.save()
        return ens

    def _enseignants(self):
        self.chef = Enseignant.objects.get(personne__nom='Ngoma')
        self.mbemba = self._enseignant('Mbemba', 'Christelle', 'F', 'enseignant')
        self.nkounkou = self._enseignant('Nkounkou', 'Arsène', 'M', 'referent')
        ref, _ = ReferentClasse.objects.get_or_create(enseignant=self.nkounkou)
        ref.classes.add(self.l1_mip, self.l1_bcg)

    def _affectations(self):
        for ec, classe, ens, heures in (
            ('ALGO1', self.l1_mip, self.mbemba, 48), ('ARCHI1', self.l1_mip, self.mbemba, 24),
            ('PROG1', self.l1_mip, self.nkounkou, 36), ('INFOBCG', self.l1_bcg, self.mbemba, 24),
            ('BDD', self.l2_info, self.mbemba, 36), ('RES', self.l2_info, self.chef, 36),
        ):
            AffectationEC.objects.get_or_create(ec=self.ec[ec], classe=classe, enseignant=ens, type_seance=None,
                                                defaults={'heures_prevues': heures})

    # ── Séances ──────────────────────────────────────────────────
    def _seance(self, ec, classe, ens, jour, creneau, statut, type_seance='CM', liee=None):
        debut, fin = CRENEAUX[creneau]
        s = Seance.objects.filter(ec=self.ec[ec], classe=classe, date_seance=jour, heure_debut=debut).first()
        if s is None:
            s = Seance(ec=self.ec[ec], classe=classe, enseignant=ens, date_seance=jour, heure_debut=debut,
                       heure_fin=fin, type_seance=type_seance, statut=statut, seance_liee=liee)
            s.save()
        return s

    def _seances(self):
        # (jour de la semaine, EC, classe, enseignant, créneau, type)
        semaine_type = [
            (0, 'ALGO1', self.l1_mip, self.mbemba, 'matin', 'CM'),
            (0, 'PROG1', self.l1_mip, self.nkounkou, 'aprem', 'TD'),
            (1, 'BDD', self.l2_info, self.mbemba, 'matin', 'CM'),
            (1, 'RES', self.l2_info, self.chef, 'aprem', 'CM'),
            (2, 'ARCHI1', self.l1_mip, self.mbemba, 'midi', 'CM'),
            (3, 'PROG1', self.l1_mip, self.nkounkou, 'matin', 'CM'),
            (3, 'BDD', self.l2_info, self.mbemba, 'aprem', 'TP'),
            (4, 'RES', self.l2_info, self.chef, 'matin', 'TD'),
            (4, 'ALGO1', self.l1_mip, self.mbemba, 'aprem', 'TD'),
        ]
        for semaine in range(SEMAINES_CONFIRMEES + 1):
            statut = 'Confirmée' if semaine < SEMAINES_CONFIRMEES else 'brouillon'
            lundi = PREMIER_LUNDI + timedelta(weeks=semaine)
            for jour, ec, classe, ens, creneau, type_seance in semaine_type:
                s = self._seance(ec, classe, ens, lundi + timedelta(days=jour), creneau, statut, type_seance)
                # Cours mutualisé : l'algorithmique du lundi est suivie aussi par la L1 BCG.
                if jour == 0 and ec == 'ALGO1':
                    self._seance('INFOBCG', self.l1_bcg, ens, lundi, creneau, statut, type_seance, liee=s)
