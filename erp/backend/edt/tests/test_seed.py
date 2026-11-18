from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from core.droits import modules_accessibles, roles_contextuels
from edt.models import AffectationEC, Seance


@override_settings(DEBUG=True)
class SeedEdtTests(TestCase):
    def setUp(self):
        call_command('seed_socle', verbosity=0)

    def test_seed_edt_idempotent(self):
        call_command('seed_edt', verbosity=0)
        nb = (Seance.objects.count(), AffectationEC.objects.count(), User.objects.count())
        call_command('seed_edt', verbosity=0)
        self.assertEqual((Seance.objects.count(), AffectationEC.objects.count(), User.objects.count()), nb)
        self.assertGreaterEqual(Seance.objects.count(), 30)
        self.assertTrue(Seance.objects.filter(statut='Confirmée').exists())
        self.assertTrue(Seance.objects.filter(statut='brouillon').exists())
        self.assertTrue(Seance.objects.filter(seance_liee__isnull=False).exists())

    def test_seances_valides(self):
        call_command('seed_edt', verbosity=0)
        for s in Seance.objects.all():
            s.full_clean()

    def test_comptes(self):
        call_command('seed_edt', verbosity=0)
        self.assertIn('referent_classe', roles_contextuels(User.objects.get(username='referent')))
        self.assertEqual(roles_contextuels(User.objects.get(username='enseignant')), ['enseignant'])
        self.assertEqual(modules_accessibles(User.objects.get(username='chef'))[0]['code'], 'edt')

    @override_settings(DEBUG=False)
    def test_refuse_hors_debug(self):
        with self.assertRaises(CommandError):
            call_command('seed_edt', verbosity=0)
