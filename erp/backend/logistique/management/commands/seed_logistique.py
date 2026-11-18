"""Données de démonstration de la Logistique (après seed_rh et seed_finance ; DEBUG seulement, idempotent)."""
from datetime import date, time

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction

from core.models import Employe
from finance import transports
from finance.models import DepenseTransport
from logistique.models import AffectationTransport, Bus, Trajet

BUS = [('01', 'CG-001-AA', 50, 'actif'), ('02', 'CG-002-AA', 35, 'actif'), ('03', 'CG-003-AA', 50, 'maintenance')]
TRAJETS = [
    ('Ligne A — Centre-ville', 'Pointe-Noire centre', 'Campus de Liambou', time(6, 30), time(7, 30)),
    ('Ligne B — Tié-Tié', 'Tié-Tié', 'Campus de Liambou', time(6, 45), time(7, 45)),
    ('Retour du soir', 'Campus de Liambou', 'Pointe-Noire centre', time(17, 0), time(18, 0)),
]
DEPENSES = [('01', 'carburant', '85000', date(2026, 10, 15), 'Plein de gazole'),
            ('02', 'carburant', '60000', date(2026, 10, 16), 'Plein de gazole'),
            ('02', 'entretien', '120000', date(2026, 11, 4), 'Vidange et filtres'),
            ('03', 'reparation', '350000', date(2026, 11, 6), 'Embrayage')]


class Command(BaseCommand):
    help = 'Crée les bus, trajets, affectations et dépenses de transport de démonstration.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_logistique est refusé quand DEBUG=False (données de démonstration).')
        if not Employe.objects.filter(fonction='chauffeur').exists():
            call_command('seed_finance', verbosity=0)
        with transaction.atomic():
            bus = {}
            for numero, plaque, capacite, statut in BUS:
                bus[numero], _ = Bus.objects.get_or_create(numero=numero, defaults={
                    'plaque': plaque, 'capacite': capacite, 'statut': 'actif'})
            trajets = [Trajet.objects.get_or_create(nom=nom, defaults={
                'depart': d, 'destination': a, 'heure_depart': hd, 'heure_arrivee': ha})[0]
                for nom, d, a, hd, ha in TRAJETS]
            chauffeurs = list(Employe.objects.filter(fonction='chauffeur').order_by('personne__nom'))[:2]
            for b, c, t in zip((bus['01'], bus['02']), chauffeurs, trajets):
                if not AffectationTransport.objects.filter(bus=b).exists():
                    AffectationTransport.objects.create(bus=b, chauffeur=c, trajet=t, date_debut=date(2026, 10, 1))
            for numero, _, _, statut in BUS:
                if bus[numero].statut != statut and not AffectationTransport.objects.filter(bus=bus[numero]).exists():
                    bus[numero].statut = statut
                    bus[numero].save()
            par = User.objects.filter(username='finance_responsable').first()
            for numero, type_, montant, jour, description in DEPENSES:
                if not DepenseTransport.objects.filter(bus=bus[numero], date=jour, type=type_).exists():
                    transports.enregistrer(bus[numero], type_, montant, date=jour, description=description, par=par,
                                           historique=True)
        self.stdout.write(self.style.SUCCESS('Logistique de démonstration prête (3 bus, 3 trajets, 2 affectations).'))
