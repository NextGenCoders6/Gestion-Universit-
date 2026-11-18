from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from finance import recus, transports
from finance.models import Operation
from logistique.tests.fabriques import bus

D = Decimal


class TransportsTests(TestCase):
    def setUp(self):
        self.b1, self.b2 = bus('01'), bus('02')

    def test_ecriture_au_journal(self):
        d = transports.enregistrer(self.b1, 'carburant', '45000', date=date(2026, 11, 3), description='Plein')
        self.assertEqual((d.operation.montant, d.operation.categorie), (D('-45000'), 'transport'))
        self.assertIn('Bus 01', d.operation.libelle)
        self.assertIn('Carburant', d.operation.libelle)

    def test_invalides_sans_ecriture(self):
        for valeur in ('0', '-10', 'abc'):
            with self.subTest(valeur=valeur), self.assertRaises(ValidationError):
                transports.enregistrer(self.b1, 'carburant', valeur)
        with self.assertRaises(ValidationError) as ctx:
            transports.enregistrer(self.b1, 'pneus', '100')
        self.assertIn('type', ctx.exception.message_dict)
        self.assertFalse(Operation.objects.exists())

    def test_annulation_et_couts(self):
        a = transports.enregistrer(self.b1, 'carburant', '45000', date=date(2026, 10, 3))
        transports.enregistrer(self.b1, 'entretien', '120000', date=date(2026, 11, 4))
        transports.enregistrer(self.b2, 'reparation', '300000', date=date(2026, 11, 5))
        contre = transports.annuler_depense(a, 'Saisie en double')
        self.assertEqual(contre.montant, D('45000'))
        with self.assertRaises(ValidationError):
            transports.annuler_depense(a, 'encore')
        c = transports.couts()
        self.assertEqual(c['total'], D('420000'))
        self.assertEqual(c['par_type'], {'entretien': D('120000'), 'reparation': D('300000')})
        self.assertEqual(c['par_bus'], [{'bus': self.b2.pk, 'numero': '02', 'total': D('300000')},
                                        {'bus': self.b1.pk, 'numero': '01', 'total': D('120000')}])
        self.assertEqual(c['par_mois'], {'2026-11': D('420000')})
        self.assertEqual(transports.couts(bus=self.b1)['total'], D('120000'))
        self.assertEqual(transports.couts(debut=date(2026, 11, 5))['total'], D('300000'))

    def test_recu(self):
        d = transports.enregistrer(self.b1, 'carburant', '45000', date=date(2026, 11, 3))
        self.assertTrue(recus.recu_operation(d.operation).startswith(b'%PDF'))
