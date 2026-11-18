from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.tests import fabriques as f
from rh.contrats import contrat_en_cours, contrats_a_echeance, terminer
from rh.models import Contrat
from rh.tests.fabriques import employe, enseignant, permanent, vacataire


class ReglesTests(TestCase):
    def setUp(self):
        self.dep = f.departement()
        self.ens = enseignant('Ngoma', self.dep).personne
        self.emp = employe().personne

    def test_personne_sans_role_refusee(self):
        with self.assertRaises(ValidationError) as ctx:
            permanent(f.personne(nom='Inconnu'))
        self.assertIn('personne', ctx.exception.message_dict)

    def test_vacataire_reserve_aux_enseignants(self):
        with self.assertRaises(ValidationError) as ctx:
            vacataire(self.emp)
        self.assertIn('type', ctx.exception.message_dict)

    def test_taux_et_salaire_obligatoires(self):
        with self.assertRaises(ValidationError) as ctx:
            Contrat.objects.create(personne=self.ens, type='vacataire', date_debut=date(2026, 9, 1))
        self.assertIn('taux_horaire', ctx.exception.message_dict)
        with self.assertRaises(ValidationError) as ctx:
            Contrat.objects.create(personne=self.emp, type='permanent', date_debut=date(2026, 9, 1),
                                   salaire_mensuel=Decimal('0'))
        self.assertIn('salaire_mensuel', ctx.exception.message_dict)

    def test_dates(self):
        with self.assertRaises(ValidationError) as ctx:
            vacataire(self.ens, debut=date(2026, 9, 1), fin=date(2026, 8, 1))
        self.assertIn('date_fin', ctx.exception.message_dict)

    def test_chevauchement_refuse(self):
        permanent(self.emp, debut=date(2025, 9, 1), fin=None)        # durée indéterminée
        with self.assertRaises(ValidationError):
            permanent(self.emp, debut=date(2030, 1, 1), fin=date(2030, 12, 31))
        vacataire(self.ens, debut=date(2026, 9, 1), fin=date(2027, 7, 31))
        with self.assertRaises(ValidationError):
            vacataire(self.ens, debut=date(2027, 7, 31), fin=date(2028, 7, 31))
        vacataire(self.ens, debut=date(2027, 8, 1), fin=date(2028, 7, 31))   # contigu : autorisé
        self.assertEqual(Contrat.objects.filter(personne=self.ens).count(), 2)


class EtatTests(TestCase):
    def setUp(self):
        self.ens = enseignant('Ngoma', f.departement()).personne
        self.c = vacataire(self.ens, debut=date(2026, 9, 1), fin=date(2026, 12, 15))

    def test_etat_et_contrat_en_cours(self):
        self.assertEqual(self.c.etat(date(2026, 8, 31)), 'a_venir')
        self.assertEqual(self.c.etat(date(2026, 12, 15)), 'en_cours')
        self.assertEqual(self.c.etat(date(2026, 12, 16)), 'expire')
        self.assertEqual(contrat_en_cours(self.ens, date(2026, 11, 18)), self.c)
        self.assertIsNone(contrat_en_cours(self.ens, date(2027, 1, 1)))

    def test_echeance(self):
        self.assertEqual(list(contrats_a_echeance(30, jour=date(2026, 11, 18))), [self.c])
        self.assertEqual(list(contrats_a_echeance(30, jour=date(2026, 10, 1))), [])

    def test_terminer(self):
        terminer(self.c, date(2026, 11, 30))
        self.c.refresh_from_db()
        self.assertEqual(self.c.date_fin, date(2026, 11, 30))
        with self.assertRaises(ValidationError):
            terminer(self.c, date(2026, 8, 1))
