from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from edt.tests.fabriques import Monde, affectation, seance_brute
from finance import paie
from finance.models import Operation, Paie
from rh import vacations
from rh.tests.fabriques import employe, permanent, vacataire

D = Decimal
AUJ = date.today()


class SalairesTests(TestCase):
    def setUp(self):
        self.m = Monde()
        self.c1 = permanent(self.m.ens.personne, debut=date(2025, 9, 1), salaire='650000')
        self.g = employe('Gardien')
        self.c2 = permanent(self.g.personne, debut=date(2026, 10, 20), fin=date(2027, 6, 30), salaire='120000')
        vacataire(self.m.ens2.personne, debut=date(2026, 9, 1), fin=date(2027, 7, 31))
        ancien = employe('Ancien')
        permanent(ancien.personne, debut=date(2024, 1, 1), fin=date(2026, 9, 30), salaire='100000')

    def test_generation_idempotente(self):
        self.assertEqual(paie.generer_salaires('2026-10'), (2, 0))
        self.assertEqual(paie.generer_salaires('2026-10'), (0, 2))
        lignes = Paie.objects.filter(mois='2026-10').order_by('montant_du')
        self.assertEqual([(l.contrat, l.montant_du, l.statut) for l in lignes],
                         [(self.c2, D('120000'), 'en_attente'), (self.c1, D('650000'), 'en_attente')])
        self.assertEqual(paie.generer_salaires('2026-09'), (2, 0))   # l'ancien gardien et l'enseignant

    def test_mois_invalide(self):
        with self.assertRaises(ValidationError):
            paie.generer_salaires('2026-13')

    def test_paiements_partiels(self):
        paie.generer_salaires('2026-10')
        ligne = Paie.objects.get(contrat=self.c1)
        p = paie.payer(ligne, '400000', 'virement', reference='VIR-1')
        self.assertEqual((p.operation.montant, p.operation.categorie), (D('-400000'), 'salaire'))
        self.assertIn('2026-10', p.operation.libelle)
        ligne.refresh_from_db()
        self.assertEqual(ligne.statut, 'partiel')
        with self.assertRaises(ValidationError):
            paie.payer(ligne, '300000', 'virement')
        paie.payer(ligne, '250000', 'virement')
        ligne.refresh_from_db()
        self.assertEqual(ligne.statut, 'paye')

    def test_ajustement_et_annulation(self):
        paie.generer_salaires('2026-10')
        ligne = Paie.objects.get(contrat=self.c2)
        paie.ajuster(ligne, '60000')
        ligne.refresh_from_db()
        self.assertEqual((ligne.montant_du, ligne.montant_ajuste), (D('60000'), True))
        p = paie.payer(ligne, '60000', 'especes')
        with self.assertRaises(ValidationError):
            paie.ajuster(ligne, '50000')
        contre = paie.annuler_paiement_paie(p, 'Mauvais bénéficiaire')
        self.assertEqual(contre.montant, D('60000'))
        ligne.refresh_from_db()
        self.assertEqual((ligne.montant_paye, ligne.statut), (D('0'), 'en_attente'))
        paie.ajuster(ligne, '120000')   # plus aucun paiement actif : ajustable


class VacationsTests(TestCase):
    def setUp(self):
        self.m = Monde()
        vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=60), fin=AUJ + timedelta(days=200), taux='5000')
        self.a = affectation(self.m.algo, self.m.l1, self.m.ens, 2)
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=AUJ - timedelta(days=3))

    def test_ligne_a_la_confirmation_et_retrait(self):
        v = vacations.confirmer(self.a)
        ligne = Paie.objects.get(vacation=v)
        self.assertEqual((ligne.origine, ligne.montant_du, ligne.personne), ('vacation', D('10000'), self.m.ens.personne))
        vacations.retirer(v, motif='Erreur')
        self.assertFalse(Paie.objects.exists())

    def test_retrait_refuse_si_payee(self):
        v = vacations.confirmer(self.a)
        p = paie.payer(Paie.objects.get(vacation=v), '10000', 'especes')
        self.assertEqual(p.operation.categorie, 'vacation')
        with self.assertRaises(ValidationError) as ctx:
            vacations.retirer(v, motif='Erreur')
        self.assertIn('paiement', str(ctx.exception))
        self.assertTrue(Paie.objects.filter(vacation=v).exists())
        paie.annuler_paiement_paie(p, 'Payé par erreur')
        vacations.retirer(v, motif='Erreur')   # paiement annulé : le retrait passe, le journal garde les lignes
        self.assertFalse(Paie.objects.exists())
        self.assertEqual(Operation.objects.count(), 2)
