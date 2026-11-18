from django.core.exceptions import ValidationError
from django.test import TestCase

from edt.models import AffectationEC
from edt.tests.fabriques import Monde, affectation, enseignant, seance_brute


class AffectationECTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_generique_puis_typee_interdite_meme_enseignant(self):
        affectation(self.m.algo, self.m.l1, self.m.ens)
        with self.assertRaises(ValidationError):
            affectation(self.m.algo, self.m.l1, self.m.ens, type_seance='CM')

    def test_typee_puis_generique_interdite_meme_enseignant(self):
        affectation(self.m.algo, self.m.l1, self.m.ens, 12, 'CM')
        with self.assertRaises(ValidationError):
            affectation(self.m.algo, self.m.l1, self.m.ens)

    def test_doublon_typee_interdit(self):
        affectation(self.m.algo, self.m.l1, self.m.ens, 12, 'CM')
        with self.assertRaises(ValidationError):
            affectation(self.m.algo, self.m.l1, self.m.ens, 6, 'CM')

    def test_generique_et_typee_enseignants_differents(self):
        affectation(self.m.algo, self.m.l1, self.m.ens)
        affectation(self.m.algo, self.m.l1, self.m.ens2, 12, 'TD')
        self.assertEqual(AffectationEC.objects.count(), 2)

    def test_meme_enseignant_autre_classe_autorise(self):
        affectation(self.m.bdd, self.m.l2, self.m.ens)
        from core.models import Classe
        from core.tests import fabriques as f
        l2_suivante = Classe.objects.create(annee=f.annee('2027-2028'), parcours=f.parcours('Licence', 2),
                                            filiere=self.m.info)
        affectation(self.m.bdd, l2_suivante, self.m.ens)
        self.assertEqual(AffectationEC.objects.count(), 2)

    def test_hors_departement_refuse_sans_drapeau(self):
        matheux = enseignant('Mavoungou', self.m.dep_math)
        with self.assertRaises(ValidationError):
            affectation(self.m.algo, self.m.l1, matheux)
        affectation(self.m.algo, self.m.l1, matheux, hors_departement=True)

    def test_ec_hors_classe_refuse(self):
        with self.assertRaises(ValidationError):
            affectation(self.m.bdd, self.m.l1, self.m.ens)  # EC de S3 dans une classe de L1

    def test_depassement_non_bloquant_avec_avertissement(self):
        a = affectation(self.m.algo, self.m.l1, self.m.ens, 20)
        self.assertFalse(a.has_volume_warning())
        b = affectation(self.m.algo, self.m.l1, self.m.ens2, 10)  # 30 h > 24 h : enregistrée quand même
        self.assertTrue(b.has_volume_warning())

    def test_heures_de_l_affectation(self):
        a = affectation(self.m.algo, self.m.l1, self.m.ens, 12, 'CM')
        seance_brute(self.m.algo, self.m.l1, self.m.ens, type_seance='CM')
        seance_brute(self.m.algo, self.m.l1, self.m.ens, type_seance='TD')
        self.assertEqual(a.heures_consommees(), 2)
        self.assertEqual(a.heures_restantes(), 10)
