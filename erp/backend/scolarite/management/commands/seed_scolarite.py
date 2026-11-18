"""Données de démonstration de la Scolarité (après seed_socle et seed_edt ; DEBUG seulement, idempotent)."""
import random
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction

from core.management.commands.seed_socle import MOT_DE_PASSE_DEMO
from core.models import (
    AnneeAcademique, Classe, Departement, ElementConstitutif, Etudiant, Faculte, ParametresEtablissement, Periode,
    Personne, Portail, UniteEnseignement,
)
from scolarite.inscriptions import inscrire
from scolarite.moteur import deliberation

NOMS = ['Mabiala', 'Moukala', 'Bouanga', 'Tchicaya', 'Nzaba', 'Mavoungou', 'Massamba', 'Kimbembe', 'Loubaki',
        'Milongo', 'Bitsindou', 'Samba', 'Ngouabi', 'Mpassi', 'Nkodia', 'Malonga', 'Ganga', 'Ibara', 'Okoko',
        'Mbouma']
PRENOMS = [('Grâce', 'F'), ('Divine', 'F'), ('Paul', 'M'), ('Rose', 'F'), ('Christ', 'M'), ('Merveille', 'F'),
           ('Junior', 'M'), ('Prisca', 'F'), ('Arnaud', 'M'), ('Exaucée', 'F'), ('Brice', 'M'), ('Ornella', 'F'),
           ('Fabrice', 'M'), ('Gloria', 'F'), ('Hervé', 'M')]

# Programme complémentaire (le socle n'a qu'une UE de S1 pour la MIP).
UES = [
    ('UE-MIP-S1-2', 'Mathématiques générales', 'S1', 'MIP',
     [('MATHG1', 'Mathématiques générales', 3, 'Informatique'), ('PHYS1', 'Physique 1', 3, 'Informatique')]),
    ('UE-BCG-S1-2', 'Sciences du vivant', 'S1', 'BCG',
     [('BIOCEL', 'Biologie cellulaire', 4, 'Biologie'), ('CHIMG', 'Chimie générale', 3, 'Biologie')]),
]

EFFECTIFS = (('L1', 'MIP', 25), ('L1', 'BCG', 20), ('L2', 'INFO', 15))


class Command(BaseCommand):
    help = 'Crée les étudiants, inscriptions, notes et une délibération de démonstration (après seed_edt).'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_scolarite est refusé quand DEBUG=False (comptes de démonstration).')
        if not ElementConstitutif.objects.filter(code='BDD').exists():
            call_command('seed_edt', verbosity=0)
        self.hasard = random.Random(2026)
        with transaction.atomic():
            self.annee = AnneeAcademique.objects.get(libelle='2026-2027')
            self._signataires()
            self._programme()
            self._annee_suivante()
            inscriptions = self._etudiants()
            self._notes(inscriptions)
            self._comptes(inscriptions)
            l1_mip = self._classe('L1', 'MIP')
            deliberation(l1_mip, 'S1', enregistrer=True, par=User.objects.filter(username='scolarite_faculte').first())
        self.stdout.write(self.style.SUCCESS(
            f'Scolarité de démonstration prête ({Etudiant.objects.count()} étudiants, compte « etudiant »).'))

    def _classe(self, niveau, code, annee=None):
        qs = Classe.objects.filter(annee=annee or self.annee, parcours__type_parcours='Licence',
                                   parcours__niveau=int(niveau[1]))
        return qs.get(portail__code=code) if niveau == 'L1' else qs.get(filiere__code=code)

    def _signataires(self):
        """Noms imprimés sur les documents officiels, s'ils ne sont pas déjà renseignés."""
        parametres = ParametresEtablissement.get()
        if not parametres.nom_secretaire:
            parametres.nom_secretaire, parametres.genre_secretaire = 'Pélagie Okandza', 'F'
            parametres.save()
        for code, nom, genre in (('FST', 'Albert Nzoussi', 'M'), ('FSE', 'Marie Ondongo', 'F')):
            fac = Faculte.objects.filter(code=code, nom_doyen='').first()
            if fac:
                fac.nom_doyen, fac.genre_doyen = nom, genre
                fac.save()

    def _programme(self):
        for code, libelle, semestre, portail, ecs in UES:
            ue, _ = UniteEnseignement.objects.get_or_create(code=code, defaults={
                'libelle': libelle, 'semestre': semestre, 'portail': Portail.objects.get(code=portail)})
            for code_ec, lib, credits, dep in ecs:
                ElementConstitutif.objects.get_or_create(code=code_ec, defaults={
                    'ue': ue, 'libelle': lib, 'credits': credits, 'departement': Departement.objects.get(libelle=dep),
                    'heures_cm': credits * 6, 'heures_td': credits * 4, 'heures_tp': credits * 2})

    def _annee_suivante(self):
        """2027-2028 avec les mêmes classes, pour essayer la promotion et l'orientation."""
        suivante, _ = AnneeAcademique.objects.get_or_create(
            libelle='2027-2028', defaults={'date_debut': date(2027, 10, 1), 'date_fin': date(2028, 7, 31)})
        Periode.objects.get_or_create(annee=suivante, numero=1,
                                      defaults={'date_debut': date(2027, 10, 1), 'date_fin': date(2028, 2, 15)})
        Periode.objects.get_or_create(annee=suivante, numero=2,
                                      defaults={'date_debut': date(2028, 2, 16), 'date_fin': date(2028, 7, 31)})
        for c in Classe.objects.filter(annee=self.annee):
            Classe.objects.get_or_create(annee=suivante, parcours=c.parcours, portail=c.portail, filiere=c.filiere)

    def _etudiants(self):
        inscriptions = []
        rang = 0
        for niveau, code, effectif in EFFECTIFS:
            classe = self._classe(niveau, code)
            for _ in range(effectif):
                nom = NOMS[rang % len(NOMS)]
                prenom, genre = PRENOMS[(rang * 7) % len(PRENOMS)]
                email = f'{self._ascii(prenom)}.{self._ascii(nom)}.{rang + 1}@etu.uccb.cg'
                naissance = date(2004 + rang % 4, 1 + rang % 12, 1 + rang % 28)
                inscriptions.append(self._inscrit(classe, nom, prenom, genre, email, naissance))
                rang += 1
        # Étudiant non activé, aux informations connues, pour essayer l'activation.
        inscriptions.append(self._inscrit(self._classe('L1', 'MIP'), 'Bakala', 'Jonas', 'M',
                                          'jonas.bakala@etu.uccb.cg', date(2006, 5, 12)))
        return inscriptions

    @staticmethod
    def _ascii(texte):
        import unicodedata
        return unicodedata.normalize('NFKD', texte).encode('ascii', 'ignore').decode().lower()

    def _inscrit(self, classe, nom, prenom, genre, email, naissance):
        personne, _ = Personne.objects.get_or_create(email=email, defaults={
            'nom': nom, 'prenom': prenom, 'genre': genre, 'date_naissance': naissance,
            'lieu_naissance': 'Brazzaville'})
        etudiant = Etudiant.objects.filter(pk=personne.pk).first() or Etudiant.objects.create(
            personne=personne, annee_entree=self.annee if classe.parcours.niveau == 1 else
            AnneeAcademique.objects.get_or_create(libelle='2025-2026', defaults={
                'date_debut': date(2025, 10, 1), 'date_fin': date(2026, 7, 31), 'statut': 'archivee'})[0])
        inscription = etudiant.inscriptions.filter(annee=self.annee).first()
        if inscription is None:
            inscription = inscrire(etudiant, classe, type='premiere' if classe.parcours.niveau == 1 else
                                   'reinscription', date=date(2026, 10, 1))
        return inscription

    def _notes(self, inscriptions):
        """Notes de S1 (S3 pour la L2) : quelques absences, un éliminatoire, quelques EC non saisis."""
        for n, inscription in enumerate(inscriptions[:-1]):
            premier = inscription.classe.semestres[0]
            niveau = self.hasard.uniform(7, 16)
            for k, note in enumerate(inscription.notes.filter(ec__ue__semestre=premier).order_by('ec__code')):
                devoir = round(min(20, max(0, self.hasard.gauss(niveau, 2.5))), 1)
                session = round(min(20, max(0, self.hasard.gauss(niveau, 2.5))), 1)
                note.note_devoir, note.note_session, note.note_sr, note.est_absent = (
                    Decimal(str(devoir)), Decimal(str(session)), None, False)
                if n in (3, 30) and k == 0:
                    note.note_devoir = note.note_session = None
                    note.est_absent = True
                elif n == 5 and k == 1:
                    note.note_devoir, note.note_session = Decimal('4'), Decimal('3.5')   # éliminatoire
                elif n in (8, 40) and k == 2:
                    note.note_devoir = note.note_session = None                         # non saisie
                note.save()

    def _comptes(self, inscriptions):
        """Compte « etudiant » activé, rattaché au premier étudiant de L1 MIP."""
        personne = inscriptions[0].etudiant.personne
        user = User.objects.filter(username='etudiant').first()
        if user is None:
            user = User.objects.create_user('etudiant', email=personne.email, password=MOT_DE_PASSE_DEMO,
                                            first_name=personne.prenom, last_name=personne.nom)
        if personne.user_id != user.pk:
            personne.user = user
            personne.save()
