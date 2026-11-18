from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from core.droits import modules_accessibles, roles_contextuels
from core.models import AnneeAcademique, Classe


@override_settings(DEBUG=True)
class SeedSocleTests(TestCase):
    def test_seed_idempotent(self):
        call_command('seed_socle', verbosity=0)
        nb_users, nb_classes = User.objects.count(), Classe.objects.count()
        call_command('seed_socle', verbosity=0)
        self.assertEqual(User.objects.count(), nb_users)
        self.assertEqual(Classe.objects.count(), nb_classes)
        self.assertEqual(AnneeAcademique.courante().libelle, '2026-2027')
        rh = User.objects.get(username='rh_responsable')
        self.assertEqual([m['code'] for m in modules_accessibles(rh)], ['rh'])
        self.assertTrue(rh.check_password('Uccb!2026demo'))

    def test_comptes_types(self):
        call_command('seed_socle', verbosity=0)
        self.assertTrue(User.objects.get(username='admin').is_superuser)
        self.assertEqual(modules_accessibles(User.objects.get(username='employe')), [])
        self.assertIn('chef_departement', roles_contextuels(User.objects.get(username='chef')))
        self.assertTrue(Classe.objects.filter(libelle='L1 MIP — 2026-2027').exists())

    @override_settings(DEBUG=False)
    def test_reset_refuse_hors_debug(self):
        with self.assertRaises(CommandError):
            call_command('seed_socle', '--reset', verbosity=0)
