from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.tests import fabriques as f
from finance import frais
from finance.models import FraisScolarite, Tarif
from finance.tests.fabriques import tarif
from scolarite.tests.fabriques import Monde, inscrit

D = Decimal


class EcheancierTests(TestCase):
    def test_dix_mensualites(self):
        lignes = frais.echeancier(D('1500000'), 10, '2026-10', 5)
        self.assertEqual(len(lignes), 10)
        self.assertEqual(lignes[0], ('2026-10', date(2026, 11, 5), D('150000')))
        self.assertEqual(lignes[-1], ('2027-07', date(2027, 8, 5), D('150000')))

    def test_arrondi(self):
        lignes = frais.echeancier(D('1500000'), 7, '2026-10', 5)
        self.assertEqual(sum(l[2] for l in lignes), D('1500000'))
        self.assertEqual([l[2] for l in lignes], [D('214285')] * 6 + [D('214290')])

    def test_decembre_et_montant_nul(self):
        self.assertEqual(frais.echeancier(D('100'), 1, '2026-12', 10), [('2026-12', date(2027, 1, 10), D('100'))])
        self.assertEqual(frais.echeancier(D('0'), 10, '2026-10', 5), [])


class TarifTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_valeurs_par_defaut(self):
        t = tarif(self.m.annee, f.parcours('Licence', 1))
        self.assertEqual((t.nombre_mensualites, t.premier_mois, t.jour_echeance), (10, '2026-10', 5))

    def test_doctorat_et_unicite(self):
        with self.assertRaises(ValidationError):
            tarif(self.m.annee, f.parcours('Doctorat', 1))
        tarif(self.m.annee, f.parcours('Licence', 1))
        with self.assertRaises(ValidationError):
            tarif(self.m.annee, f.parcours('Licence', 1))

    def test_bornes(self):
        with self.assertRaises(ValidationError):
            tarif(self.m.annee, f.parcours('Licence', 1), nombre_mensualites=13)
        with self.assertRaises(ValidationError):
            tarif(self.m.annee, f.parcours('Licence', 2), jour_echeance=31)
        with self.assertRaises(ValidationError):
            tarif(self.m.annee, f.parcours('Licence', 3), premier_mois='2026-13')


class DossierTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_cree_avec_l_inscription(self):
        tarif(self.m.annee, self.m.l1.parcours)
        d = inscrit(self.m.l1).frais
        self.assertEqual((d.montant_du, d.montant_paye, d.statut), (D('1500000'), D('0'), 'non_paye'))
        self.assertEqual(d.echeances.count(), 10)
        self.assertEqual(d.echeances.first().date_limite, date(2026, 11, 5))

    def test_sans_tarif_puis_tarif_cree(self):
        d = inscrit(self.m.l1).frais
        self.assertEqual((d.montant_du, d.echeances.count()), (D('0'), 0))
        tarif(self.m.annee, self.m.l1.parcours, '1000000', nombre_mensualites=4)
        d.refresh_from_db()
        self.assertEqual((d.montant_du, d.echeances.count()), (D('1000000'), 4))

    def test_tarif_modifie_epargne_les_dossiers_ajustes(self):
        t = tarif(self.m.annee, self.m.l1.parcours)
        a = inscrit(self.m.l1, 'Alpha').frais
        b = inscrit(self.m.l1, 'Beta').frais
        frais.ajuster(b, D('750000'))
        t.montant = D('1800000')
        t.save()
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual((a.montant_du, b.montant_du), (D('1800000'), D('750000')))
        self.assertEqual(sum(e.montant for e in b.echeances.all()), D('750000'))
        self.assertEqual(b.echeances.count(), 10)

    def test_trop_percu(self):
        t = tarif(self.m.annee, self.m.l1.parcours)
        d = inscrit(self.m.l1).frais
        FraisScolarite.objects.filter(pk=d.pk).update(montant_paye=D('1200000'))
        t.montant = D('1000000')
        t.save()
        d.refresh_from_db()
        self.assertEqual((d.statut, d.trop_percu, d.reste), ('paye', D('200000'), D('0')))

    def test_rattrapage_idempotent(self):
        i = inscrit(self.m.l1)
        i.frais.delete()
        self.assertEqual(frais.creer_dossiers_manquants(), 1)
        self.assertEqual(frais.creer_dossiers_manquants(), 0)


class EtatEcheancesTests(TestCase):
    def setUp(self):
        self.m = Monde()
        tarif(self.m.annee, self.m.l1.parcours)   # 10 × 150 000, 05/11/2026 → 05/08/2027
        self.d = inscrit(self.m.l1).frais

    def payer(self, montant):
        FraisScolarite.objects.filter(pk=self.d.pk).update(montant_paye=D(montant))
        self.d.refresh_from_db()

    def test_etats(self):
        self.payer('225000')   # une mensualité et demie
        etats = frais.etat_echeances(self.d, jour=date(2026, 11, 20))
        self.assertEqual([e['etat'] for e in etats[:3]], ['payee', 'partielle', 'a_venir'])
        self.assertEqual(etats[1]['paye'], D('75000'))
        self.assertFalse(frais.en_retard(self.d, jour=date(2026, 11, 20)))
        etats = frais.etat_echeances(self.d, jour=date(2026, 12, 6))
        self.assertEqual(etats[1]['etat'], 'en_retard')
        self.assertTrue(frais.en_retard(self.d, jour=date(2026, 12, 6)))
        self.assertEqual(frais.montant_en_retard(self.d, jour=date(2026, 12, 6)), D('75000'))
        self.assertEqual(frais.prochaine_echeance(self.d, jour=date(2026, 12, 6))['numero'], 2)

    def test_a_jour_et_solde(self):
        self.assertFalse(frais.en_retard(self.d, jour=date(2026, 11, 5)))
        self.assertTrue(frais.en_retard(self.d, jour=date(2026, 11, 6)))
        self.payer('1500000')
        self.assertFalse(frais.en_retard(self.d, jour=date(2027, 9, 1)))
        self.assertIsNone(frais.prochaine_echeance(self.d, jour=date(2027, 9, 1)))


class AdaptationTests(TestCase):
    def setUp(self):
        self.m = Monde()
        self.t = tarif(self.m.annee, self.m.l1.parcours, '900000')
        self.d = inscrit(self.m.l1).frais

    def test_adapter(self):
        frais.adapter_echeancier(self.d, [('2027-01', date(2027, 2, 5), D('450000')),
                                          ('2027-02', date(2027, 3, 5), D('450000'))])
        self.d.refresh_from_db()
        self.assertTrue(self.d.echeancier_adapte)
        self.assertEqual(self.d.echeances.count(), 2)
        self.t.nombre_mensualites = 3
        self.t.save()
        self.assertEqual(self.d.echeances.count(), 2)   # échéancier adapté conservé

    def test_somme_ou_dates_invalides(self):
        with self.assertRaises(ValidationError):
            frais.adapter_echeancier(self.d, [('2027-01', date(2027, 2, 5), D('100'))])
        with self.assertRaises(ValidationError):
            frais.adapter_echeancier(self.d, [('2027-02', date(2027, 3, 5), D('450000')),
                                              ('2027-01', date(2027, 2, 5), D('450000'))])
        self.assertEqual(self.d.echeances.count(), 10)
