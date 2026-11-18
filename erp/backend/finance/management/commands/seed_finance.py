"""Données de démonstration de la Finance (après seed_rh ; DEBUG seulement, idempotent)."""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from django.utils import timezone

from core.models import AnneeAcademique, Classe, Etudiant, Filiere, Parcours, Personne
from finance import frais, paie, paiements
from finance.models import FraisScolarite, Operation, Paie, Tarif
from scolarite.inscriptions import inscrire

ANNUEL = Decimal('1500000')
MENSUALITE = ANNUEL / 10
MODES = ['especes', 'mobile_money', 'virement', 'cheque']


class Command(BaseCommand):
    help = 'Crée les tarifs, les paiements de frais, la paie et le journal de démonstration (après seed_rh).'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_finance est refusé quand DEBUG=False (données de démonstration).')
        if not AnneeAcademique.objects.filter(libelle='2026-2027').exists():
            call_command('seed_rh', verbosity=0)
        with transaction.atomic():
            self.annee = AnneeAcademique.objects.get(libelle='2026-2027')
            self.caisse = User.objects.filter(username='finance_utilisateur').first()
            self.responsable = User.objects.filter(username='finance_responsable').first()
            self._tarifs()
            self._master_sans_tarif()
            frais.creer_dossiers_manquants()
            self._paiements_frais()
            self._paie()
            self._operations()
        self.stdout.write(self.style.SUCCESS('Finance de démonstration prête (tarifs, paiements, paie, journal).'))

    def _tarifs(self):
        for niveau in (1, 2, 3):
            parcours = Parcours.objects.get(type_parcours='Licence', niveau=niveau)
            if not Tarif.objects.filter(annee=self.annee, parcours=parcours).exists():
                Tarif.objects.create(annee=self.annee, parcours=parcours, montant=ANNUEL, nombre_mensualites=10,
                                     jour_echeance=5)

    def _master_sans_tarif(self):
        """Une classe de M1 et un étudiant : le cas « dossier sans tarif » (tarif à créer dans Paramètres)."""
        info = Filiere.objects.get(code='INFO')
        m1, _ = Classe.objects.get_or_create(annee=self.annee, parcours=Parcours.objects.get(type_parcours='Master',
                                                                                              niveau=1), filiere=info)
        personne, _ = Personne.objects.get_or_create(email='prisca.mavoungou@etu.uccb.cg', defaults={
            'nom': 'Mavoungou', 'prenom': 'Prisca', 'genre': 'F', 'date_naissance': date(2002, 4, 9)})
        etudiant = Etudiant.objects.filter(pk=personne.pk).first() or Etudiant.objects.create(
            personne=personne, annee_entree=self.annee)
        if not etudiant.inscriptions.filter(annee=self.annee).exists():
            inscrire(etudiant, m1, type='premiere', date=date(2026, 10, 1))

    def _paiements_frais(self):
        """Profils variés : à jour, soldé, en retard, partiel en retard, sans paiement."""
        etudiant = User.objects.filter(username='etudiant').first()
        dossiers = (FraisScolarite.objects.filter(inscription__annee=self.annee, montant_du__gt=0)
                    .select_related('inscription__etudiant__personne').order_by('pk'))
        for n, dossier in enumerate(dossiers):
            if dossier.paiements.exists():
                continue
            if etudiant and dossier.inscription.etudiant.personne.user_id == etudiant.pk:
                # Compte de démonstration : à jour à la date du seed (mensualités échues + la suivante).
                jour = timezone.localdate()
                echues = [e.montant for e in dossier.echeances.all() if e.date_limite < jour]
                montant = min(dossier.montant_du, sum(echues, Decimal('0')) + MENSUALITE)
            else:
                montant = {0: dossier.montant_du, 1: MENSUALITE, 2: MENSUALITE * 2, 3: Decimal('0'),
                           4: MENSUALITE / 2}[n % 5]
            if montant > 0:
                paiements.encaisser(dossier, montant, MODES[n % 4], date=date(2026, 10, 10 + n % 15),
                                    reference=f'DEMO-{n:03d}', par=self.caisse, historique=True)

    def _paie(self):
        paie.generer_salaires('2026-10', par=self.responsable)
        for n, ligne in enumerate(Paie.objects.filter(mois='2026-10').order_by('pk')):
            if n % 2 == 0 and not ligne.paiements.exists():
                paie.payer(ligne, ligne.montant_du, 'virement', date=date(2026, 10, 31), par=self.responsable,
                           historique=True)
        from rh.models import Vacation
        for vacation in Vacation.objects.all():
            ligne = Paie.objects.filter(vacation=vacation).first() or paie.creer_ligne_vacation(vacation)
            if not ligne.paiements.exists():
                paie.payer(ligne, ligne.montant_du, 'mobile_money', date=date(2026, 11, 2), par=self.responsable,
                           historique=True)

    def _operations(self):
        for libelle, montant, jour in (('Don de la paroisse Saint-Esprit', '250000', date(2026, 10, 20)),
                                       ('Achat de fournitures de bureau', '-85000', date(2026, 11, 3))):
            if not Operation.objects.filter(libelle=libelle).exists():
                paiements.operation_manuelle(libelle, montant, jour, par=self.responsable, historique=True)
