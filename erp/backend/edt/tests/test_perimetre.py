from django.contrib.auth.models import User
from django.test import TestCase

from core.droits import a_droit, definir_droits, modules_accessibles, roles_contextuels
from core.models import Classe
from core.tests import fabriques as f
from edt.models import ReferentClasse
from edt.perimetre import classes_autorisees, classes_gerables, restreindre_enseignants
from edt.tests.fabriques import Monde, enseignant


def compte_de(ens, username):
    u = User.objects.create_user(username, password='Mot-de-passe-1')
    p = ens.personne
    p.user = u
    p.save()
    return u


class PerimetreTests(TestCase):
    def setUp(self):
        self.m = Monde()
        # chef du département Informatique
        self.m.dep.chef = self.m.ens
        self.m.dep.save()
        self.chef = compte_de(self.m.ens, 'chef')
        self.simple = compte_de(self.m.ens2, 'simple')
        self.math = enseignant('Mavoungou', self.m.dep_math)
        fil_math = f.filiere(self.m.dep_math, self.m.mip, 'MATH')
        self.l2_math = Classe.objects.create(annee=self.m.annee, parcours=f.parcours('Licence', 2), filiere=fil_math)

    def test_chef_gere_les_classes_de_son_departement(self):
        self.assertEqual(set(classes_gerables(self.chef)), {self.m.l2})

    def test_l1_reservee_au_referent(self):
        self.assertNotIn(self.m.l1, classes_gerables(self.chef))
        ref = ReferentClasse.objects.create(enseignant=self.math)
        ref.classes.add(self.m.l1)
        u = compte_de(self.math, 'referent')
        self.assertEqual(set(classes_gerables(u)), {self.m.l1})

    def test_chef_et_referent_cumulent(self):
        ref = ReferentClasse.objects.create(enseignant=self.m.ens)
        ref.classes.add(self.m.l1)
        self.assertEqual(set(classes_gerables(self.chef)), {self.m.l1, self.m.l2})

    def test_responsable_illimite(self):
        u = User.objects.create_user('resp', password='Mot-de-passe-1')
        definir_droits(u, ['edt_responsable'])
        self.assertIsNone(classes_gerables(u))
        self.assertIsNone(classes_autorisees(u))

    def test_utilisateur_lit_tout_sans_gerer(self):
        u = User.objects.create_user('lecteur', password='Mot-de-passe-1')
        definir_droits(u, ['edt_utilisateur'])
        self.assertIsNone(classes_autorisees(u))
        self.assertEqual(list(classes_gerables(u)), [])

    def test_enseignant_simple_ne_gere_rien(self):
        self.assertEqual(list(classes_gerables(self.simple)), [])

    def test_restreindre_enseignants(self):
        """Comme l'EDT : liste complète pour un chef (affectations inter-départements), département sinon."""
        from core.models import Enseignant
        tous = Enseignant.objects.all()
        self.assertEqual(restreindre_enseignants(self.chef, tous).count(), 3)
        noms = {e.personne.nom for e in restreindre_enseignants(self.simple, tous)}
        self.assertEqual(noms, {'Ngoma', 'Okemba'})
        sans_fiche = User.objects.create_user('x', password='Mot-de-passe-1')
        self.assertEqual(restreindre_enseignants(sans_fiche, tous).count(), 0)


class DroitsContextuelsTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_tuile_edt_pour_chef_sans_groupe(self):
        self.m.dep.chef = self.m.ens
        self.m.dep.save()
        u = compte_de(self.m.ens, 'chef')
        self.assertEqual(modules_accessibles(u), [{'code': 'edt', 'libelle': 'Emploi du temps', 'niveaux': ['perimetre']}])
        self.assertTrue(a_droit(u, 'edt', 'perimetre'))
        self.assertFalse(a_droit(u, 'edt', 'responsable'))

    def test_role_referent(self):
        ref = ReferentClasse.objects.create(enseignant=self.m.ens2)
        u = compte_de(self.m.ens2, 'ref')
        self.assertNotIn('referent_classe', roles_contextuels(u))  # sans classe
        ref.classes.add(self.m.l1)
        self.assertIn('referent_classe', roles_contextuels(u))
        self.assertTrue(a_droit(u, 'edt'))

    def test_enseignant_simple_sans_tuile(self):
        u = compte_de(self.m.ens2, 'simple')
        self.assertEqual(modules_accessibles(u), [])
        self.assertEqual(roles_contextuels(u), ['enseignant'])

    def test_groupe_et_perimetre_cumules(self):
        self.m.dep.chef = self.m.ens
        self.m.dep.save()
        u = compte_de(self.m.ens, 'chef')
        definir_droits(u, ['edt_utilisateur'])
        self.assertEqual(modules_accessibles(u)[0]['niveaux'], ['utilisateur', 'perimetre'])
