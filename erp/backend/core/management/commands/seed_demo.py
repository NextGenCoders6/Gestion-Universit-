"""Remplit tout l'ERP de démonstration en une commande (DEBUG seulement, idempotent)."""
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError, call_command

from core.management.commands.seed_socle import MOT_DE_PASSE_DEMO

ETAPES = ['seed_edt', 'seed_scolarite', 'seed_rh', 'seed_finance', 'seed_logistique']

PROFILS = [
    ('admin', 'superutilisateur : tous les modules'),
    ('parametres', 'Paramètres (référentiel, utilisateurs, tarifs)'),
    ('scolarite_secretariat', 'Scolarité — secrétariat (étudiants, inscriptions, documents)'),
    ('scolarite_faculte', 'Scolarité — faculté FST (notes, délibérations, vacations)'),
    ('edt_responsable', 'Emploi du temps — responsable'), ('edt_utilisateur', 'Emploi du temps — lecture'),
    ('rh_responsable', 'RH — responsable'), ('rh_utilisateur', 'RH — lecture'),
    ('finance_responsable', 'Finance — responsable (paie, ajustements, transports)'),
    ('finance_utilisateur', 'Finance — caisse (encaissements)'),
    ('logistique_responsable', 'Logistique — responsable'), ('logistique_utilisateur', 'Logistique — lecture'),
    ('chef', 'chef du département Informatique (EDT de son département)'),
    ('referent', 'référent des L1 MIP et BCG (EDT)'), ('enseignant', 'enseignante : Mon espace'),
    ('etudiant', 'étudiant de L1 MIP : Mon espace (notes, planning, frais)'), ('employe', 'employé sans module'),
]


class Command(BaseCommand):
    help = "Crée les données de démonstration de tout l'ERP (socle, EDT, Scolarité, RH, Finance, Logistique)."

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Vide d’abord toutes les données (DEBUG seulement).')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_demo est refusé quand DEBUG=False (comptes de démonstration).')
        call_command('seed_socle', reset=options['reset'], verbosity=0)
        for etape in ETAPES:
            call_command(etape, verbosity=0)
        self.stdout.write(self.style.SUCCESS("ERP de démonstration prêt."))
        self.stdout.write(f'Mot de passe de tous les comptes : {MOT_DE_PASSE_DEMO}')
        for identifiant, role in PROFILS:
            if User.objects.filter(username=identifiant).exists():
                self.stdout.write(f'  {identifiant:<24} {role}')
