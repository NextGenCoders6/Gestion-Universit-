from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from core.models import Employe
from edt.models import AffectationEC
from rh import vacations
from rh.contrats import contrat_en_cours, contrats_a_echeance
from rh.models import Contrat, Vacation


@override_settings(DEBUG=True)
class SeedRhTests(TestCase):
    def setUp(self):
        call_command('seed_socle', verbosity=0)
        call_command('seed_edt', verbosity=0)
        call_command('seed_rh', verbosity=0)

    def test_idempotent(self):
        avant = (Contrat.objects.count(), Employe.objects.count(), Vacation.objects.count())
        call_command('seed_rh', verbosity=0)
        self.assertEqual((Contrat.objects.count(), Employe.objects.count(), Vacation.objects.count()), avant)

    def test_jeu_de_donnees(self):
        self.assertGreaterEqual(Employe.objects.count(), 10)
        chauffeurs = [e for e in Employe.objects.filter(fonction='chauffeur') if contrat_en_cours(e.personne)]
        self.assertEqual(len(chauffeurs), 2)
        self.assertTrue(contrats_a_echeance(30).exists())
        self.assertTrue(Contrat.objects.filter(date_fin__lt='2026-11-18').exists())
        self.assertEqual(Vacation.objects.count(), 1)
        affectations = list(AffectationEC.objects.select_related('enseignant__personne'))
        heures = vacations.Heures(affectations)
        a_confirmer = [a for a in affectations if (e := vacations.etat(a, heures))['terminee']
                       and e['vacation'] is None and e['confirmable']]
        self.assertGreaterEqual(len(a_confirmer), 1)

    @override_settings(DEBUG=False)
    def test_refuse_hors_debug(self):
        with self.assertRaises(CommandError):
            call_command('seed_rh', verbosity=0)
