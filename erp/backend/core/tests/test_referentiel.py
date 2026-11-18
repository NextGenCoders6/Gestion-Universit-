from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import (
    AnneeAcademique, Classe, ElementConstitutif, Faculte, Filiere, Parcours,
    ParametresEtablissement, Periode, UniteEnseignement,
)
from core.tests import fabriques as f


class AnneeAcademiqueTests(TestCase):
    def test_libelle_format_invalide(self):
        with self.assertRaisesMessage(ValidationError, 'AAAA-AAAA'):
            AnneeAcademique.objects.create(
                libelle='2026/2027', date_debut=date(2026, 10, 1), date_fin=date(2027, 7, 31)
            )

    def test_annee_fin_doit_suivre(self):
        with self.assertRaises(ValidationError):
            AnneeAcademique.objects.create(
                libelle='2026-2028', date_debut=date(2026, 10, 1), date_fin=date(2028, 7, 31)
            )

    def test_une_seule_annee_en_cours(self):
        a = f.annee('2025-2026', en_cours=True)
        b = f.annee('2026-2027', en_cours=True)
        a.refresh_from_db()
        self.assertFalse(a.en_cours)
        self.assertEqual(AnneeAcademique.courante(), b)

    def test_courante_sans_annee(self):
        self.assertIsNone(AnneeAcademique.courante())


class PeriodeTests(TestCase):
    def test_periode_hors_annee_refusee(self):
        a = f.annee()
        with self.assertRaises(ValidationError) as ctx:
            Periode.objects.create(annee=a, numero=1, date_debut=date(2026, 9, 1), date_fin=date(2027, 1, 31))
        self.assertIn('date_debut', ctx.exception.message_dict)

    def test_periode_valide(self):
        p = f.periode(f.annee(), 2)
        self.assertEqual(p.numero, 2)


class FaculteTests(TestCase):
    def test_titres_doyen_selon_genre(self):
        fac = Faculte.objects.create(nom='Sciences', code='FST', genre_doyen='F', nom_doyen='A. Mavoungou')
        self.assertEqual(fac.titre_doyen, 'La Doyenne')
        self.assertEqual(fac.titre_vice_doyen, 'Le Vice-Doyen')


class ParcoursTests(TestCase):
    def test_code_et_semestres(self):
        self.assertEqual(Parcours(type_parcours='Licence', niveau=2).code, 'L2')
        self.assertEqual(Parcours(type_parcours='Licence', niveau=2).semestres, ('S3', 'S4'))
        self.assertEqual(Parcours(type_parcours='Licence', niveau=1).semestres, ('S1', 'S2'))
        self.assertEqual(Parcours(type_parcours='Master', niveau=1).semestres, ('S7', 'S8'))
        self.assertEqual(Parcours(type_parcours='Master', niveau=2).code, 'M2')

    def test_niveau_max(self):
        with self.assertRaises(ValidationError):
            Parcours.objects.create(type_parcours='Licence', niveau=4)


class ClasseTests(TestCase):
    def setUp(self):
        self.annee = f.annee()
        self.portail = f.portail()
        self.filiere = f.filiere(port=self.portail)

    def test_l1_sur_portail_libelle(self):
        c = Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 1), portail=self.portail)
        self.assertEqual(c.libelle, 'L1 MIP — 2026-2027')

    def test_l2_sur_filiere_libelle(self):
        c = Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 2), filiere=self.filiere)
        self.assertEqual(c.libelle, 'L2 INFO — 2026-2027')

    def test_l1_avec_filiere_refusee(self):
        with self.assertRaises(ValidationError):
            Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 1), filiere=self.filiere)

    def test_l2_sans_filiere_refusee(self):
        with self.assertRaises(ValidationError):
            Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 2), portail=self.portail)

    def test_portail_et_filiere_refuses(self):
        with self.assertRaises(ValidationError):
            Classe.objects.create(
                annee=self.annee, parcours=f.parcours('Licence', 1), portail=self.portail, filiere=self.filiere
            )

    def test_ni_portail_ni_filiere_refuse(self):
        with self.assertRaises(ValidationError):
            Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 1))

    def test_doctorat_refuse(self):
        with self.assertRaises(ValidationError):
            Classe.objects.create(annee=self.annee, parcours=f.parcours('Doctorat', 1), filiere=self.filiere)

    def test_unicite(self):
        Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 1), portail=self.portail)
        with self.assertRaises(ValidationError):
            Classe.objects.create(annee=self.annee, parcours=f.parcours('Licence', 1), portail=self.portail)


class UETests(TestCase):
    def test_s1_sur_portail_ok_s3_sur_portail_refuse(self):
        f.ue('UE1', 'S1', port=f.portail())
        with self.assertRaises(ValidationError):
            f.ue('UE3', 'S3', port=f.portail())

    def test_s1_sur_filiere_refuse(self):
        with self.assertRaises(ValidationError):
            f.ue('UE1', 'S1', fil=f.filiere())

    def test_periode_numero(self):
        self.assertEqual(UniteEnseignement(semestre='S3').periode_numero, 1)
        self.assertEqual(UniteEnseignement(semestre='S4').periode_numero, 2)
        self.assertEqual(UniteEnseignement(semestre='S10').periode_numero, 2)


class ECTests(TestCase):
    def test_credits_bornes(self):
        u = f.ue()
        for i, credits in enumerate([0, 7]):
            with self.assertRaises(ValidationError):
                f.ec(u, code=f'EC-KO{i}', credits=credits)
        self.assertEqual(f.ec(u, code='EC-1', credits=1).credits, 1)
        self.assertEqual(f.ec(u, code='EC-6', credits=6).credits, 6)

    def test_heures_total(self):
        e = ElementConstitutif(heures_cm=20, heures_td=10, heures_tp=5)
        self.assertEqual(e.heures_total, 35)


class FiliereTests(TestCase):
    def test_portail_et_departement_meme_faculte(self):
        dep = f.departement(f.faculte('FST'))
        port = f.portail(f.faculte('FSE'), code='ECO')
        with self.assertRaises(ValidationError):
            Filiere.objects.create(departement=dep, portail=port, nom='Info', code='INFO')


class ParametresEtablissementTests(TestCase):
    def test_singleton_et_titre(self):
        p = ParametresEtablissement.get()
        self.assertEqual(p.ville_signature, 'Liambou')
        self.assertEqual(ParametresEtablissement.get().pk, p.pk)
        p.genre_secretaire = 'F'
        self.assertEqual(p.titre_secretaire, 'La Secrétaire Universitaire')
