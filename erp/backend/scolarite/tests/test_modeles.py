from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import AnneeAcademique, Classe
from core.tests import fabriques as f
from scolarite import inscriptions
from scolarite.inscriptions import inscrire
from scolarite.models import Inscription, Note, ResultatSemestre
from scolarite.tests.fabriques import Monde, etudiant, inscrit, noter


class FormuleTests(TestCase):
    def setUp(self):
        self.m = Monde()
        self.i = inscrit(self.m.l1)

    def test_moyenne_normale(self):
        n = noter(self.i, self.m.algo, devoir=12, session=15)
        self.assertEqual(n.calculer(), 13.5)
        self.assertEqual(n.moyenne, Decimal('13.50'))

    def test_sr_meilleure_retenue(self):
        # normale (4+6)/2 = 5 ; SR (4 + 2×14)/3 = 10.67
        self.assertEqual(noter(self.i, self.m.algo, devoir=4, session=6, sr=14).calculer(), 10.67)

    def test_sr_moins_bonne_ignoree(self):
        # normale (12+10)/2 = 11 ; SR (12 + 2×3)/3 = 6
        self.assertEqual(noter(self.i, self.m.algo, devoir=12, session=10, sr=3).calculer(), 11.0)

    def test_absent_vaut_zero(self):
        n = noter(self.i, self.m.algo, absent=True)
        self.assertEqual(n.calculer(), 0.0)
        self.assertEqual(n.moyenne, Decimal('0'))

    def test_non_saisi_sans_moyenne(self):
        self.assertIsNone(self.i.notes.get(ec=self.m.algo).moyenne)
        n = noter(self.i, self.m.algo, devoir=12)
        self.assertIsNone(n.calculer())
        self.assertIsNone(n.moyenne)

    def test_sr_sans_session_refusee(self):
        with self.assertRaises(ValidationError) as ctx:
            noter(self.i, self.m.algo, devoir=12, sr=14)
        self.assertIn('note_sr', ctx.exception.message_dict)

    def test_bornes(self):
        for valeur in (21, -1):
            with self.subTest(valeur=valeur), self.assertRaises(ValidationError):
                noter(self.i, self.m.algo, devoir=valeur, session=10)


class InscriptionTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_notes_creees_pour_s1_et_s2(self):
        i = inscrit(self.m.l1)
        self.assertEqual(i.annee, self.m.annee)
        self.assertEqual(set(i.notes.values_list('ec__code', flat=True)), {'ALGO', 'PROG', 'ANALYSE', 'RESEAU'})
        self.assertEqual(i.type, 'premiere')
        self.assertEqual(i.statut, 'active')

    def test_une_seule_inscription_par_annee(self):
        e = etudiant(annee=self.m.annee)
        inscrire(e, self.m.l1, type='premiere')
        with self.assertRaises(ValidationError):
            inscrire(e, self.m.l2, type='reinscription')
        self.assertEqual(Inscription.objects.count(), 1)
        self.assertEqual(Note.objects.count(), 4)

    def test_annee_suivante_autorisee(self):
        e = etudiant(annee=self.m.annee)
        inscrire(e, self.m.l1, type='premiere')
        suivante = f.annee('2027-2028')
        l2 = Classe.objects.create(annee=suivante, parcours=f.parcours('Licence', 2), filiere=self.m.info)
        i = inscrire(e, l2, type='reinscription')
        self.assertEqual(set(i.notes.values_list('ec__code', flat=True)), {'BDD'})

    def test_classe_archivee_refusee(self):
        AnneeAcademique.objects.filter(pk=self.m.annee.pk).update(statut='archivee', en_cours=False)
        with self.assertRaises(ValidationError):
            inscrit(Classe.objects.get(pk=self.m.l1.pk))

    def test_rappels_appeles(self):
        appels = []
        inscriptions.APRES_INSCRIPTION.append(appels.append)
        try:
            i = inscrit(self.m.l1)
        finally:
            inscriptions.APRES_INSCRIPTION.remove(appels.append)
        self.assertEqual(appels, [i])

    def test_programme_de_classe(self):
        self.assertEqual(set(self.m.l1.ecs_au_programme().values_list('code', flat=True)),
                         {'ALGO', 'PROG', 'ANALYSE', 'RESEAU'})
        self.assertEqual(set(self.m.l2.ecs_au_programme().values_list('code', flat=True)), {'BDD'})


class ResultatTests(TestCase):
    def test_un_resultat_par_semestre(self):
        m = Monde()
        i = inscrit(m.l1)
        ResultatSemestre.objects.create(inscription=i, semestre='S1', moyenne=12, credits_obtenus=10,
                                        credits_totaux=10, decision='ADMIS', mention='PASSABLE', rang=1)
        with self.assertRaises(ValidationError):
            ResultatSemestre.objects.create(inscription=i, semestre='S1', moyenne=12, credits_obtenus=10,
                                            credits_totaux=10, decision='ADMIS', mention='PASSABLE', rang=1)

    def test_semestre_hors_niveau_refuse(self):
        m = Monde()
        i = inscrit(m.l1)
        with self.assertRaises(ValidationError):
            ResultatSemestre.objects.create(inscription=i, semestre='S3', moyenne=12, credits_obtenus=0,
                                            credits_totaux=0, decision='AJOURNÉ', mention='NÉANT')
