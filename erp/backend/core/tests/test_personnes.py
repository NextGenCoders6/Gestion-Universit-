from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Employe, Enseignant, Etudiant, Personne
from core.tests import fabriques as f


class PersonneTests(TestCase):
    def test_suspension_exige_motif(self):
        p = f.personne()
        p.statut = 'suspendu'
        with self.assertRaises(ValidationError) as ctx:
            p.save()
        self.assertIn('motif_suspension', ctx.exception.message_dict)
        p.motif_suspension = 'Dossier incomplet'
        p.save()
        self.assertTrue(p.est_suspendue)

    def test_nom_invalide(self):
        with self.assertRaises(ValidationError):
            f.personne(nom='J3an')

    def test_nom_complet(self):
        self.assertEqual(f.personne(nom='Mabiala', prenom='Grâce').nom_complet, 'MABIALA Grâce')

    def test_email_unique_mais_optionnel(self):
        f.personne(nom='Un', email='')
        f.personne(nom='Deux', email='')
        f.personne(nom='Trois', email='a@uccb.cg')
        with self.assertRaises(ValidationError):
            f.personne(nom='Quatre', email='a@uccb.cg')

    def test_date_naissance_future_refusee(self):
        with self.assertRaises(ValidationError):
            f.personne(date_naissance=date(2100, 1, 1))


class MatriculeTests(TestCase):
    def test_matricule_etudiant(self):
        p = f.personne(nom='Mabiala', prenom='Grâce')
        e = Etudiant.objects.create(personne=p, annee_entree=f.annee('2026-2027'))
        self.assertRegex(e.matricule, r'^UCCB26MABGR\d{5}$')

    def test_matricule_nom_court(self):
        p = f.personne(nom='Ba', prenom='N')
        e = Etudiant.objects.create(personne=p, annee_entree=f.annee('2026-2027'))
        self.assertRegex(e.matricule, r'^UCCB26BAXNX\d{5}$')

    def test_matricules_etudiants_distincts(self):
        a = Etudiant.objects.create(personne=f.personne(nom='Mabiala', prenom='Grâce'), annee_entree=f.annee())
        b = Etudiant.objects.create(personne=f.personne(nom='Mabiala', prenom='Grâce'), annee_entree=f.annee())
        self.assertNotEqual(a.matricule, b.matricule)

    def test_matricule_enseignant_et_employe(self):
        ens = Enseignant.objects.create(personne=f.personne(nom='Ngoma'), departement=f.departement())
        emp = Employe.objects.create(personne=f.personne(nom='Loemba'), fonction='gardien')
        self.assertEqual(ens.matricule, 'UCCB-ENS-00001')
        self.assertEqual(emp.matricule, 'UCCB-PERS-00001')
        ens2 = Enseignant.objects.create(personne=f.personne(nom='Okemba'), departement=f.departement())
        self.assertEqual(ens2.matricule, 'UCCB-ENS-00002')

    def test_matricule_conserve_a_la_modification(self):
        ens = Enseignant.objects.create(personne=f.personne(), departement=f.departement())
        ens.grade = 'Docteur'
        ens.save()
        self.assertEqual(Enseignant.objects.get(pk=ens.pk).matricule, 'UCCB-ENS-00001')


class RolesTests(TestCase):
    def test_cumul_roles(self):
        p = f.personne()
        Enseignant.objects.create(personne=p, departement=f.departement())
        Employe.objects.create(personne=p, fonction='technicien')
        p.refresh_from_db()
        self.assertTrue(hasattr(p, 'enseignant'))
        self.assertTrue(hasattr(p, 'employe'))

    def test_fonction_autre_exige_libelle(self):
        with self.assertRaises(ValidationError):
            Employe.objects.create(personne=f.personne(), fonction='autre')
        emp = Employe.objects.create(personne=f.personne(nom='Autre'), fonction='autre', fonction_autre='Jardinier')
        self.assertEqual(emp.fonction_libelle, 'Jardinier')

    def test_chef_de_departement(self):
        dep = f.departement()
        ens = Enseignant.objects.create(personne=f.personne(), departement=dep)
        dep.chef = ens
        dep.save()
        self.assertEqual(list(ens.departements_diriges.all()), [dep])
