"""Données de démonstration des RH (après seed_edt ; DEBUG seulement, idempotent)."""
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from django.utils import timezone

from core.models import Employe, Enseignant, Faculte, Personne
from edt.models import AffectationEC
from rh import vacations
from rh.models import Contrat

DEBUT = date(2026, 9, 1)
FIN_ANNEE = date(2027, 7, 31)

# (nom, prénom, genre, fonction, fonction_autre, salaire)
PERSONNEL = [
    ('Nzaba', 'Didier', 'M', 'chauffeur', '', '180000'),
    ('Malonga', 'Jean', 'M', 'chauffeur', '', '180000'),
    ('Moussavou', 'Léa', 'F', 'menage', '', '110000'),
    ('Kimbembe', 'Rachel', 'F', 'menage', '', '110000'),
    ('Ganga', 'Pierre', 'M', 'cuisinier', '', '140000'),
    ('Ibara', 'Serge', 'M', 'technicien', '', '200000'),
    ('Okoko', 'Bruno', 'M', 'gardien', '', '120000'),
    ('Loubaki', 'Nadège', 'F', 'autre', 'Bibliothécaire', '190000'),
    ('Samba', 'Victor', 'M', 'gardien', '', '120000'),
]


class Command(BaseCommand):
    help = 'Crée les contrats, le personnel et des vacations de démonstration (après seed_edt).'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_rh est refusé quand DEBUG=False (données de démonstration).')
        if not Enseignant.objects.filter(personne__nom='Mbemba').exists():
            call_command('seed_edt', verbosity=0)
        aujourdhui = timezone.localdate()
        with transaction.atomic():
            self._contrats_enseignants(aujourdhui)
            self._personnel(aujourdhui)
            self._vacations()
        self.stdout.write(self.style.SUCCESS('RH de démonstration prêtes (contrats, personnel, vacations).'))

    def _contrat(self, personne, type, debut=DEBUT, fin=FIN_ANNEE, montant='0', **kw):
        if personne.contrats.exists():
            return personne.contrats.order_by('-date_debut').first()
        champ = 'taux_horaire' if type == 'vacataire' else 'salaire_mensuel'
        return Contrat.objects.create(personne=personne, type=type, date_debut=debut, date_fin=fin,
                                      **{champ: Decimal(montant)}, **kw)

    def _contrats_enseignants(self, aujourdhui):
        plan = {
            'Ngoma': ('permanent', DEBUT.replace(year=2020), None, '650000'),
            'Okemba': ('permanent', DEBUT.replace(year=2022), None, '600000'),
            'Mbemba': ('vacataire', DEBUT, FIN_ANNEE, '6000'),
            'Nkounkou': ('vacataire', DEBUT, FIN_ANNEE, '5500'),
            'Loemba': ('vacataire', DEBUT, aujourdhui + timedelta(days=15), '5000'),       # à échéance
            'Mavoungou': ('vacataire', date(2025, 10, 1), date(2026, 7, 31), '5000'),      # expiré
        }
        for ens in Enseignant.objects.select_related('personne'):
            type, debut, fin, montant = plan.get(ens.personne.nom, ('vacataire', DEBUT, FIN_ANNEE, '5000'))
            self._contrat(ens.personne, type, debut, fin, montant, diplome='Doctorat' if type == 'permanent' else 'Master',
                          rib=f'CG39 3001 0000 {ens.pk:04d} {ens.pk * 7 % 10000:04d}')

    def _personnel(self, aujourdhui):
        fst = Faculte.objects.filter(code='FST').first()
        for i, (nom, prenom, genre, fonction, autre, salaire) in enumerate(PERSONNEL):
            personne, _ = Personne.objects.get_or_create(nom=nom, prenom=prenom, defaults={'genre': genre})
            Employe.objects.get_or_create(personne=personne, defaults={
                'fonction': fonction, 'fonction_autre': autre, 'lieu_travail': 'Campus de Liambou',
                'faculte_rattachement': fst if fonction in ('technicien', 'autre') else None})
            if nom == 'Samba':   # ancien gardien : contrat expiré
                self._contrat(personne, 'permanent', date(2024, 1, 1), date(2026, 6, 30), salaire)
            else:
                self._contrat(personne, 'permanent', DEBUT.replace(year=2025 - i % 3), None, salaire)
        gardien = Personne.objects.filter(nom='Bouanga', prenom='Marc').first()
        if gardien is not None:
            self._contrat(gardien, 'permanent', date(2023, 9, 1), None, '120000')

    def _affectation_terminee(self, code, libelle, nom, samedi):
        """EC de L2 INFO propre à la démo RH, avec deux séances passées qui couvrent ses heures prévues.

        Le seed ne touche pas aux affectations de seed_edt : les scénarios de l'EDT s'en servent.
        """
        from datetime import time
        from core.models import Classe, Departement, ElementConstitutif, UniteEnseignement
        from edt.models import Seance
        ue = UniteEnseignement.objects.get(code='UE-INFO-S3-1')
        ec, _ = ElementConstitutif.objects.get_or_create(code=code, defaults={
            'ue': ue, 'libelle': libelle, 'credits': 2, 'departement': Departement.objects.get(libelle='Informatique'),
            'heures_cm': 12, 'heures_td': 8, 'heures_tp': 4})
        classe = Classe.objects.get(annee__libelle='2026-2027', parcours__niveau=2, filiere__code='INFO')
        enseignant = Enseignant.objects.get(personne__nom=nom)
        a, _ = AffectationEC.objects.get_or_create(ec=ec, classe=classe, enseignant=enseignant, type_seance=None,
                                                   defaults={'heures_prevues': 4})
        self._notes(ec, classe)
        for debut, fin in ((time(9, 0), time(11, 0)), (time(11, 15), time(13, 15))):
            if not Seance.objects.filter(ec=ec, classe=classe, date_seance=samedi, heure_debut=debut).exists():
                Seance.objects.create(ec=ec, classe=classe, enseignant=enseignant, date_seance=samedi, heure_debut=debut,
                                      heure_fin=fin, type_seance='CM', statut='Confirmée')
        return a

    @staticmethod
    def _notes(ec, classe):
        """L'EC ajouté au programme reçoit ses lignes de notes (notées) : la délibération de S3 reste complète."""
        from decimal import Decimal as D
        from scolarite.models import Note
        for n, inscription in enumerate(classe.inscriptions.exclude(statut='abandonnee').order_by('pk')):
            note, _ = Note.objects.get_or_create(inscription=inscription, ec=ec)
            if note.moyenne is None:
                note.note_devoir, note.note_session = D(str(10 + n % 7)), D(str(11 + n % 6))
                note.save()

    def _vacations(self):
        self._affectation_terminee('SYSEXP', "Systèmes d'exploitation", 'Nkounkou', date(2026, 10, 31))   # à confirmer
        a = self._affectation_terminee('WEB1', 'Développement web', 'Mbemba', date(2026, 10, 24))          # confirmée
        if not vacations.Vacation.objects.filter(affectation=a).exists():
            e = vacations.etat(a)
            if e['terminee'] and e['confirmable']:
                vacations.confirmer(a, par=User.objects.filter(username='scolarite_faculte').first())
