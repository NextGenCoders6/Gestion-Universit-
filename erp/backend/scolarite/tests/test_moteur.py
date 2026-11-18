from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from scolarite.models import ResultatSemestre
from scolarite.moteur import deliberation, ligne_etudiant, mention
from scolarite.tests.fabriques import Monde, inscrit, noter


class Base(TestCase):
    def setUp(self):
        self.m = Monde()

    def eleve(self, nom, algo, prog, analyse):
        """Chaque note est (devoir, session), 'abs' ou None (non saisie)."""
        i = inscrit(self.m.l1, nom=nom)
        for ec, valeur in ((self.m.algo, algo), (self.m.prog, prog), (self.m.analyse, analyse)):
            if valeur == 'abs':
                noter(i, ec, absent=True)
            elif valeur is not None:
                noter(i, ec, devoir=valeur[0], session=valeur[1])
        return i


class MentionTests(TestCase):
    def test_bornes(self):
        attendu = {9.99: 'NÉANT', 10: 'PASSABLE', 11.99: 'PASSABLE', 12: 'ASSEZ BIEN', 13.99: 'ASSEZ BIEN',
                   14: 'BIEN', 15.99: 'BIEN', 16: 'TRÈS BIEN', 20: 'TRÈS BIEN'}
        for moyenne, texte in attendu.items():
            with self.subTest(moyenne=moyenne):
                self.assertEqual(mention(moyenne), texte)


class LigneTests(Base):
    def test_admis(self):
        ligne = ligne_etudiant(self.eleve('Admis', (12, 14), (10, 10), (11, 13)), 'S1')
        self.assertEqual(ligne['moyenne'], 11.7)
        self.assertEqual((ligne['decision'], ligne['mention']), ('ADMIS', 'PASSABLE'))
        self.assertEqual((ligne['credits_valides'], ligne['credits_totaux']), (10, 10))
        self.assertFalse(ligne['eliminatoire'])
        self.assertEqual([u['ue'].code for u in ligne['ues']], ['UE-INF-11', 'UE-MAT-11'])
        self.assertEqual(ligne['ues'][0]['moyenne_ue'], 11.5)
        self.assertTrue(all(u['validee'] for u in ligne['ues']))

    def test_eliminatoire_ajourne_malgre_la_moyenne(self):
        ligne = ligne_etudiant(self.eleve('Elim', (4, 6), (18, 18), (16, 16)), 'S1')
        self.assertEqual(ligne['moyenne'], 13.3)
        self.assertTrue(ligne['eliminatoire'])
        self.assertEqual((ligne['decision'], ligne['mention']), ('AJOURNÉ', 'NÉANT'))

    def test_compensation_entre_ue(self):
        ligne = ligne_etudiant(self.eleve('Comp', (8, 8), (8, 8), (14, 14)), 'S1')
        self.assertEqual((ligne['moyenne'], ligne['decision']), (10.4, 'ADMIS'))
        self.assertEqual(ligne['credits_valides'], 10)
        self.assertTrue(ligne['ues'][0]['validee'])

    def test_ajourne_ue_validee_a_six(self):
        ligne = ligne_etudiant(self.eleve('Ajour', 'abs', (10, 10), (12, 12)), 'S1')
        self.assertEqual((ligne['moyenne'], ligne['decision']), (7.8, 'AJOURNÉ'))
        self.assertEqual([u['validee'] for u in ligne['ues']], [False, True])
        self.assertEqual(ligne['credits_valides'], 4)
        self.assertTrue(ligne['ues'][0]['ecs'][0]['absent'])

    def test_ec_non_saisi_ignore(self):
        ligne = ligne_etudiant(self.eleve('Trou', (12, 12), None, (12, 12)), 'S1')
        self.assertEqual(ligne['moyenne'], 12.0)
        self.assertEqual(ligne['ecs_non_saisis'], ['PROG'])
        self.assertEqual(ligne['credits_totaux'], 10)
        prog = ligne['ues'][0]['ecs'][1]
        self.assertTrue(prog['non_saisi'])
        self.assertIsNone(prog['note'])

    def test_rien_saisi(self):
        ligne = ligne_etudiant(self.eleve('Vide', None, None, None), 'S1')
        self.assertEqual((ligne['moyenne'], ligne['decision'], ligne['credits_valides']), (0.0, 'AJOURNÉ', 0))
        self.assertEqual(len(ligne['ecs_non_saisis']), 3)

    def test_semestre_hors_niveau(self):
        with self.assertRaises(ValueError):
            ligne_etudiant(self.eleve('X', None, None, None), 'S3')


class DeliberationTests(Base):
    def setUp(self):
        super().setUp()
        self.a = self.eleve('Alpha', (12, 12), (12, 12), (12, 12))
        self.b = self.eleve('Beta', (16, 16), (16, 16), (16, 16))
        self.c = self.eleve('Gamma', (10, 10), (10, 10), (10, 10))

    def test_rang_par_moyenne_decroissante(self):
        lignes = deliberation(self.m.l1, 'S1')
        self.assertEqual([(l['inscription'], l['rang']) for l in lignes], [(self.b, 1), (self.a, 2), (self.c, 3)])
        self.assertFalse(ResultatSemestre.objects.exists())

    def test_abandon_exclu(self):
        self.c.statut = 'abandonnee'
        self.c.save()
        self.assertEqual(len(deliberation(self.m.l1, 'S1')), 2)

    def test_enregistrement_idempotent(self):
        jury = User.objects.create_user('jury')
        deliberation(self.m.l1, 'S1', enregistrer=True, par=jury)
        noter(self.c, self.m.algo, devoir=20, session=20)
        deliberation(self.m.l1, 'S1', enregistrer=True, par=jury)
        self.assertEqual(ResultatSemestre.objects.count(), 3)
        r = ResultatSemestre.objects.get(inscription=self.c)
        self.assertEqual((float(r.moyenne), r.decision, r.mention, r.credits_obtenus, r.credits_totaux),
                         (13.0, 'ADMIS', 'ASSEZ BIEN', 10, 10))
        self.assertEqual((r.rang, r.delibere_par), (2, jury))
        self.assertIsNotNone(r.delibere_le)

    def test_requetes_independantes_du_nombre(self):
        with CaptureQueriesContext(connection) as avant:
            deliberation(self.m.l1, 'S1')
        for nom in ('Delta', 'Epsilon', 'Zeta', 'Eta'):
            self.eleve(nom, (11, 11), (11, 11), None)
        with CaptureQueriesContext(connection) as apres:
            self.assertEqual(len(deliberation(self.m.l1, 'S1')), 7)
        self.assertEqual(len(apres), len(avant))


class EnregistrementMoyenneSousDixTests(Base):
    def test_moyenne_a_un_chiffre(self):
        i = self.eleve('Ajour', 'abs', (10, 10), (12, 12))   # moyenne 7.8
        deliberation(self.m.l1, 'S1', enregistrer=True)
        self.assertEqual(str(ResultatSemestre.objects.get(inscription=i).moyenne), '7.80')
