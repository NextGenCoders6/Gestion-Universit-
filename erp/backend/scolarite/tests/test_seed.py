from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from core.droits import roles_contextuels
from core.models import AnneeAcademique, Classe, Etudiant
from scolarite.models import Inscription, Note, ResultatSemestre
from scolarite.moteur import deliberation


@override_settings(DEBUG=True)
class SeedScolariteTests(TestCase):
    def setUp(self):
        call_command('seed_socle', verbosity=0)
        call_command('seed_edt', verbosity=0)
        call_command('seed_scolarite', verbosity=0)

    def compter(self):
        return (Etudiant.objects.count(), Inscription.objects.count(), Note.objects.filter(moyenne__isnull=False)
                .count(), ResultatSemestre.objects.count(), User.objects.count(), Classe.objects.count())

    def test_idempotent(self):
        avant = self.compter()
        call_command('seed_scolarite', verbosity=0)
        self.assertEqual(self.compter(), avant)
        self.assertGreaterEqual(avant[0], 55)

    def test_jeu_de_donnees(self):
        l1_mip = Classe.objects.get(annee__libelle='2026-2027', parcours__niveau=1, portail__code='MIP')
        notes = Note.objects.filter(inscription__classe=l1_mip, ec__ue__semestre='S1')
        self.assertTrue(notes.filter(est_absent=True).exists())
        self.assertTrue(notes.filter(moyenne__lt=6, est_absent=False).exists())
        self.assertTrue(notes.filter(moyenne__isnull=True).exists())
        lignes = deliberation(l1_mip, 'S1')
        enregistres = {r.inscription_id: r for r in ResultatSemestre.objects.filter(inscription__classe=l1_mip)}
        self.assertEqual(len(enregistres), len(lignes))
        for ligne in lignes:
            r = enregistres[ligne['inscription'].pk]
            self.assertEqual((float(r.moyenne), r.decision, r.rang), (ligne['moyenne'], ligne['decision'],
                                                                        ligne['rang']))
        self.assertEqual({l['decision'] for l in lignes}, {'ADMIS', 'AJOURNÉ'})

    def test_comptes_et_annee_suivante(self):
        etudiant = User.objects.get(username='etudiant')
        self.assertIn('etudiant', roles_contextuels(etudiant))
        self.assertTrue(etudiant.check_password('Uccb!2026demo'))
        suivante = AnneeAcademique.objects.get(libelle='2027-2028')
        self.assertFalse(suivante.en_cours)
        self.assertTrue(Classe.objects.filter(annee=suivante, parcours__niveau=2, filiere__code='INFO').exists())
        # Un étudiant non activé, pour essayer l'activation.
        self.assertTrue(Etudiant.objects.filter(personne__user__isnull=True, personne__email='jonas.bakala@etu.uccb.cg')
                        .exists())

    def test_reset_du_socle_possible(self):
        call_command('seed_socle', '--reset', verbosity=0)
        self.assertFalse(Inscription.objects.exists())
        self.assertTrue(Classe.objects.exists())

    @override_settings(DEBUG=False)
    def test_refuse_hors_debug(self):
        with self.assertRaises(CommandError):
            call_command('seed_scolarite', verbosity=0)
