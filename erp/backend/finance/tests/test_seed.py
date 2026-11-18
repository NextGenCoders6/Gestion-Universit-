from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.db.models import Sum
from django.test import TestCase, override_settings

from finance import frais
from finance.models import FraisScolarite, Operation, Paie, PaiementEtudiant, PaiementPaie, Tarif


@override_settings(DEBUG=True)
class SeedFinanceTests(TestCase):
    def setUp(self):
        for commande in ('seed_socle', 'seed_edt', 'seed_scolarite', 'seed_rh', 'seed_finance'):
            call_command(commande, verbosity=0)

    def compter(self):
        return (Tarif.objects.count(), FraisScolarite.objects.count(), PaiementEtudiant.objects.count(),
                Paie.objects.count(), PaiementPaie.objects.count(), Operation.objects.count())

    def test_idempotent(self):
        avant = self.compter()
        call_command('seed_finance', verbosity=0)
        self.assertEqual(self.compter(), avant)

    def test_coherence(self):
        somme = lambda qs: qs.aggregate(s=Sum('montant'))['s'] or Decimal('0')
        attendu = (somme(PaiementEtudiant.objects.filter(annule=False)) - somme(PaiementPaie.objects.filter(annule=False))
                   + somme(Operation.objects.filter(categorie='manuelle')))
        self.assertEqual(somme(Operation.objects.all()), attendu)
        self.assertFalse(FraisScolarite.objects.filter(inscription__frais__isnull=True).exists())
        jour = date(2026, 11, 18)
        dossiers = list(FraisScolarite.objects.exclude(montant_du=0))
        self.assertTrue(any(frais.en_retard(d, jour) for d in dossiers))
        self.assertTrue(any(not frais.en_retard(d, jour) and d.statut == 'partiel' for d in dossiers))
        self.assertTrue(any(d.statut == 'paye' for d in dossiers))
        self.assertTrue(FraisScolarite.objects.filter(montant_du=0, inscription__classe__parcours__type_parcours='Master')
                        .exists())
        etudiant = User.objects.get(username='etudiant').personne.etudiant
        self.assertFalse(frais.en_retard(etudiant.inscriptions.get().frais, jour))
        self.assertTrue(Paie.objects.filter(mois='2026-10', montant_paye__gt=0).exists())
        self.assertTrue(Paie.objects.filter(origine='vacation', montant_paye__gt=0).exists())

    @override_settings(DEBUG=False)
    def test_refuse_hors_debug(self):
        with self.assertRaises(CommandError):
            call_command('seed_finance', verbosity=0)
