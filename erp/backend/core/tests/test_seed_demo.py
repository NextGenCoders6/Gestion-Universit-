from io import StringIO

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from core.droits import tous_les_groupes
from core.models import Employe, Etudiant
from finance.models import DepenseTransport, Operation
from logistique import affectations
from logistique.models import AffectationTransport, Bus


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def setUp(self):
        self.sortie = StringIO()
        call_command('seed_demo', stdout=self.sortie)

    def compter(self):
        return (User.objects.count(), Etudiant.objects.count(), Bus.objects.count(), AffectationTransport.objects.count(),
                DepenseTransport.objects.count(), Operation.objects.count())

    def test_idempotent(self):
        avant = self.compter()
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(self.compter(), avant)

    def test_contenu(self):
        self.assertGreaterEqual(Etudiant.objects.count(), 55)
        self.assertEqual(Bus.objects.count(), 3)
        self.assertEqual(Bus.objects.filter(statut='maintenance').count(), 1)
        self.assertEqual(affectations.actives(affectations.timezone.localdate()).count(), 2)
        self.assertTrue(DepenseTransport.objects.exists())
        self.assertGreaterEqual(Employe.objects.filter(fonction='chauffeur').count(), 2)
        groupes = [g for g in tous_les_groupes() if g != 'parametres_responsable']   # compte « parametres »
        for nom in ['admin', 'parametres', 'chef', 'enseignant', 'referent', 'etudiant', *groupes]:
            self.assertTrue(User.objects.filter(username=nom).exists(), nom)
        texte = self.sortie.getvalue()
        self.assertIn('Uccb!2026demo', texte)
        self.assertIn('logistique_responsable', texte)

    def test_reset(self):
        call_command('seed_demo', '--reset', stdout=StringIO())
        self.assertEqual(Bus.objects.count(), 3)
        self.assertEqual(AffectationTransport.objects.count(), 2)

    @override_settings(DEBUG=False)
    def test_refuse_hors_debug(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo', stdout=StringIO())
