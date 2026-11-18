from datetime import date
from unittest import mock

from django.test import TestCase

from finance import paie, paiements, recus
from finance.models import Paie
from finance.tests.fabriques import tarif
from rh.tests.fabriques import employe, permanent
from scolarite.tests.fabriques import Monde, inscrit


class RecusTests(TestCase):
    def setUp(self):
        self.m = Monde()
        tarif(self.m.annee, self.m.l1.parcours)
        self.p = paiements.encaisser(inscrit(self.m.l1, 'Alpha').frais, '300000', 'especes', date=date(2026, 11, 2))

    def test_recu_etudiant(self):
        contenu = recus.recu_paiement_etudiant(self.p)
        self.assertTrue(contenu.startswith(b'%PDF'))
        contexte = recus.contexte_paiement_etudiant(self.p)
        self.assertEqual((contexte['reste'], contexte['annule']), (1200000, False))

    def test_mention_annule(self):
        paiements.annuler_paiement(self.p, 'Erreur')
        self.p.refresh_from_db()
        with mock.patch('finance.recus.rendre_pdf', return_value=b'%PDF') as rendu:
            recus.recu_paiement_etudiant(self.p)
        self.assertTrue(rendu.call_args[0][1]['annule'])
        html = recus.html_recu('finance/recu_etudiant.html', recus.contexte_paiement_etudiant(self.p))
        self.assertIn('ANNULÉ', html)

    def test_recu_paie_et_operation(self):
        g = employe('Gardien')
        permanent(g.personne, debut=date(2026, 1, 1), salaire='120000')
        paie.generer_salaires('2026-10')
        pp = paie.payer(Paie.objects.get(), '120000', 'virement', date=date(2026, 11, 3))
        self.assertTrue(recus.recu_paiement_paie(pp).startswith(b'%PDF'))
        op = paiements.operation_manuelle('Don', '50000', date(2026, 11, 3))
        self.assertTrue(recus.recu_operation(op).startswith(b'%PDF'))
