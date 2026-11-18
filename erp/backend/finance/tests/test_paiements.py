from datetime import date, timedelta
from unittest import mock
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from finance import paiements
from finance.models import Operation, PaiementEtudiant
from finance.tests.fabriques import tarif
from scolarite.tests.fabriques import Monde, inscrit

D = Decimal


class Base(TestCase):
    def setUp(self):
        self.m = Monde()
        tarif(self.m.annee, self.m.l1.parcours)
        self.d = inscrit(self.m.l1, 'Alpha').frais
        self.caisse = User.objects.create_user('caisse')


class EncaissementTests(Base):
    def test_partiel_puis_solde(self):
        p = paiements.encaisser(self.d, '600000', 'especes', par=self.caisse)
        self.d.refresh_from_db()
        self.assertEqual((self.d.montant_paye, self.d.statut), (D('600000'), 'partiel'))
        self.assertEqual((p.operation.montant, p.operation.categorie), (D('600000'), 'frais'))
        self.assertIn('ALPHA', p.operation.libelle)
        paiements.encaisser(self.d, D('900000'), 'mobile_money', reference='MM-123')
        self.d.refresh_from_db()
        self.assertEqual(self.d.statut, 'paye')

    def test_depassement_refuse_sans_ecriture(self):
        paiements.encaisser(self.d, '1000000', 'especes')
        with self.assertRaises(ValidationError) as ctx:
            paiements.encaisser(self.d, '600000', 'especes')
        self.assertIn('500', str(ctx.exception.message_dict['montant']))
        self.assertEqual((PaiementEtudiant.objects.count(), Operation.objects.count()), (1, 1))
        self.d.refresh_from_db()
        self.assertEqual(self.d.montant_paye, D('1000000'))

    def test_montants_invalides(self):
        for valeur in ('0', '-5', 'abc', '1e30', ''):
            with self.subTest(valeur=valeur), self.assertRaises(ValidationError) as ctx:
                paiements.encaisser(self.d, valeur, 'especes')
            self.assertIn('montant', ctx.exception.message_dict)
        self.assertFalse(Operation.objects.exists())

    @mock.patch('finance.journal.timezone.localdate', return_value=date(2026, 11, 18))
    def test_mode_et_date(self, _):
        with self.assertRaises(ValidationError) as ctx:
            paiements.encaisser(self.d, '100', 'bitcoin')
        self.assertIn('mode', ctx.exception.message_dict)
        with self.assertRaises(ValidationError) as ctx:
            paiements.encaisser(self.d, '100', 'especes', date=timezone.localdate() + timedelta(days=1))
        self.assertIn('date', ctx.exception.message_dict)
        p = paiements.encaisser(self.d, '100', 'especes', date=date(2026, 11, 2))
        self.assertEqual((p.date, p.operation.date), (date(2026, 11, 2), date(2026, 11, 2)))

    def test_dossier_sans_tarif(self):
        d = inscrit(self.m.l2, 'Beta').frais
        with self.assertRaises(ValidationError):
            paiements.encaisser(d, '100', 'especes')

    @mock.patch('finance.journal.timezone.localdate', return_value=date(2026, 11, 18))
    def test_numeros_consecutifs(self, _):
        a = paiements.encaisser(self.d, '100', 'especes', date=date(2026, 11, 2))
        b = paiements.encaisser(self.d, '100', 'especes', date=date(2026, 11, 3))
        self.assertEqual((a.operation.numero, b.operation.numero), ('OP-2026-000001', 'OP-2026-000002'))
        c = paiements.encaisser(self.d, '100', 'especes', date=date(2025, 12, 31))
        self.assertEqual(c.operation.numero, 'OP-2025-000001')


class AnnulationTests(Base):
    def test_annulation(self):
        p = paiements.encaisser(self.d, '600000', 'especes')
        with self.assertRaises(ValidationError):
            paiements.annuler_paiement(p, '')
        op = paiements.annuler_paiement(p, 'Erreur de dossier', par=self.caisse)
        self.assertEqual((op.montant, op.categorie, op.annule), (D('-600000'), 'annulation', p.operation))
        p.refresh_from_db()
        self.d.refresh_from_db()
        self.assertTrue(p.annule)
        self.assertEqual((self.d.montant_paye, self.d.statut), (D('0'), 'non_paye'))
        with self.assertRaises(ValidationError):
            paiements.annuler_paiement(p, 'encore')
        self.assertEqual(Operation.objects.count(), 2)


class OperationManuelleTests(TestCase):
    def test_recette_depense_et_annulation(self):
        recette = paiements.operation_manuelle('Don de la paroisse', '250000', date(2026, 11, 3))
        depense = paiements.operation_manuelle('Achat de craies', '-15000', date(2026, 11, 4))
        self.assertEqual((recette.categorie, depense.montant), ('manuelle', D('-15000')))
        with self.assertRaises(ValidationError):
            paiements.operation_manuelle('Rien', '0', date(2026, 11, 4))
        with self.assertRaises(ValidationError):
            paiements.operation_manuelle('', '10', date(2026, 11, 4))
        contre = paiements.annuler_operation(depense, 'Saisie en double')
        self.assertEqual(contre.montant, D('15000'))
        with self.assertRaises(ValidationError):
            paiements.annuler_operation(depense, 'encore')
        p = Operation.objects.create(numero='OP-X', date=date(2026, 11, 4), libelle='frais', montant=D('1'),
                                     categorie='frais')
        with self.assertRaises(ValidationError):
            paiements.annuler_operation(p, 'non')   # un paiement s'annule par son propre paiement
