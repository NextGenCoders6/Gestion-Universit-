"""Règles de validation des séances (portées de l'EDT)."""
from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import AnneeAcademique, Periode
from edt.models import Seance
from edt.tests.fabriques import Monde, affectation, enseignant, seance_brute

LUNDI = date(2026, 10, 5)


def nouvelle(m, ec=None, classe=None, ens=None, jour=LUNDI, debut=time(9, 0), fin=time(11, 0),
             statut='Confirmée', type_seance='CM', **kw):
    return Seance.objects.create(ec=ec or m.algo, classe=classe or m.l1, enseignant=ens or m.ens,
                                 date_seance=jour, heure_debut=debut, heure_fin=fin, statut=statut,
                                 type_seance=type_seance, **kw)


class HorairesTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_creneau_valide(self):
        self.assertEqual(nouvelle(self.m).statut, 'Confirmée')

    def test_avant_9h_refuse(self):
        with self.assertRaises(ValidationError) as ctx:
            nouvelle(self.m, debut=time(8, 0))
        self.assertIn('heure_debut', ctx.exception.message_dict)

    def test_apres_16h20_refuse(self):
        with self.assertRaises(ValidationError):
            nouvelle(self.m, debut=time(14, 15), fin=time(16, 30))

    def test_debut_apres_fin_refuse(self):
        with self.assertRaises(ValidationError):
            nouvelle(self.m, debut=time(10, 0), fin=time(9, 30))

    def test_pause_meridienne_refusee(self):
        with self.assertRaises(ValidationError):
            nouvelle(self.m, debut=time(13, 0), fin=time(14, 0))

    def test_dimanche_refuse(self):
        with self.assertRaises(ValidationError) as ctx:
            nouvelle(self.m, jour=date(2026, 10, 11))
        self.assertIn('date_seance', ctx.exception.message_dict)


class CalendrierTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_hors_periode_refuse(self):
        with self.assertRaises(ValidationError) as ctx:
            nouvelle(self.m, jour=date(2027, 3, 1))  # période 2, EC de S1
        self.assertIn('date_seance', ctx.exception.message_dict)

    def test_periode_non_definie_400(self):
        Periode.objects.filter(annee=self.m.annee, numero=1).delete()
        with self.assertRaises(ValidationError) as ctx:
            nouvelle(self.m)
        self.assertIn("n'est pas définie", ctx.exception.message_dict['date_seance'][0])

    def test_annee_archivee_refuse(self):
        AnneeAcademique.objects.filter(pk=self.m.annee.pk).update(statut='archivee', en_cours=False)
        self.m.l1.annee.refresh_from_db()
        with self.assertRaises(ValidationError):
            nouvelle(self.m)

    def test_ec_hors_programme_refuse(self):
        with self.assertRaises(ValidationError) as ctx:
            nouvelle(self.m, ec=self.m.bdd)
        self.assertIn('ec', ctx.exception.message_dict)

    def test_archivage_refuse_si_seances_futures(self):
        a = self.m.annee
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=date(2099, 1, 5))
        a.statut, a.en_cours = 'archivee', False
        with self.assertRaises(ValidationError):
            a.save()


class ConflitsTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_conflit_enseignant(self):
        nouvelle(self.m)
        with self.assertRaises(ValidationError):
            nouvelle(self.m, classe=self.m.l2, ec=self.m.bdd, jour=date(2026, 10, 5))

    def test_conflit_classe(self):
        nouvelle(self.m)
        with self.assertRaises(ValidationError):
            nouvelle(self.m, ens=self.m.ens2, debut=time(10, 0), fin=time(11, 0))

    def test_brouillon_ne_cree_pas_de_conflit(self):
        nouvelle(self.m, statut='brouillon')
        nouvelle(self.m, ens=self.m.ens2)

    def test_doublon_de_brouillon_refuse(self):
        nouvelle(self.m, statut='brouillon')
        with self.assertRaises(ValidationError):
            nouvelle(self.m, statut='brouillon')

    def test_seance_liee_exempte_le_conflit_enseignant(self):
        """Cours mutualisé : même enseignant, même créneau, deux classes (chacune son EC)."""
        from core.models import Classe
        from core.tests import fabriques as f
        bcg = Classe.objects.create(annee=self.m.annee, parcours=f.parcours('Licence', 1),
                                    portail=f.portail(self.m.fac, 'BCG'))
        ec_bcg = f.ec(f.ue('UE-BCG', 'S1', port=bcg.portail), 'ALGO-BCG', credits=2, dep=self.m.dep)
        a = nouvelle(self.m)
        with self.assertRaises(ValidationError):  # sans lien : conflit enseignant
            nouvelle(self.m, ec=ec_bcg, classe=bcg)
        b = nouvelle(self.m, ec=ec_bcg, classe=bcg, seance_liee=a)
        self.assertEqual(b.seance_liee, a)

    def test_seance_liee_autre_enseignant_ou_creneau_refusee(self):
        from core.models import Classe
        from core.tests import fabriques as f
        bcg = Classe.objects.create(annee=self.m.annee, parcours=f.parcours('Licence', 1),
                                    portail=f.portail(self.m.fac, 'BCG'))
        ec_bcg = f.ec(f.ue('UE-BCG', 'S1', port=bcg.portail), 'ALGO-BCG', credits=2, dep=self.m.dep)
        a = nouvelle(self.m)
        with self.assertRaises(ValidationError):
            nouvelle(self.m, ec=ec_bcg, classe=bcg, ens=self.m.ens2, seance_liee=a)
        with self.assertRaises(ValidationError):
            nouvelle(self.m, ec=ec_bcg, classe=bcg, debut=time(11, 15), fin=time(13, 15), seance_liee=a)


class VolumesTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_quota_ec_depasse(self):
        for i, jour in enumerate([5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 19, 20]):  # 12 × 2 h = 24 h
            nouvelle(self.m, jour=date(2026, 10, jour))
        with self.assertRaises(ValidationError):
            nouvelle(self.m, jour=date(2026, 10, 21))

    def test_enseignant_non_affecte_refuse_quand_affectations_existent(self):
        affectation(self.m.algo, self.m.l1, self.m.ens2, 12)
        with self.assertRaises(ValidationError):
            nouvelle(self.m)
        nouvelle(self.m, ens=self.m.ens2)

    def test_affectation_depassee(self):
        affectation(self.m.algo, self.m.l1, self.m.ens, 2, 'CM')
        nouvelle(self.m)
        with self.assertRaises(ValidationError):
            nouvelle(self.m, jour=date(2026, 10, 6))

    def test_hors_departement_autorise_avec_affectation(self):
        matheux = enseignant('Mavoungou', self.m.dep_math)
        with self.assertRaises(ValidationError):
            nouvelle(self.m, ens=matheux)
        affectation(self.m.algo, self.m.l1, matheux, 12, hors_departement=True)
        nouvelle(self.m, ens=matheux)

    def test_plafond_six_heures_par_jour(self):
        nouvelle(self.m, debut=time(9, 0), fin=time(11, 0))
        nouvelle(self.m, ens=self.m.ens2, debut=time(11, 15), fin=time(13, 15))
        nouvelle(self.m, ens=enseignant('Trois', self.m.dep), debut=time(14, 15), fin=time(16, 15))
        self.assertEqual(Seance.objects.count(), 3)  # 6 h exactement

    def test_reportee_compte_sur_son_nouveau_jour(self):
        s = nouvelle(self.m)
        s.statut, s.date_report = 'Reportée', date(2026, 10, 6)
        s.heure_debut_report, s.heure_fin_report = time(9, 0), time(11, 0)
        s.save()
        nouvelle(self.m, ens=self.m.ens2)  # le créneau d'origine est libéré


class ReportTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_report_incomplet_refuse(self):
        s = nouvelle(self.m)
        s.statut, s.date_report = 'Reportée', date(2026, 10, 6)
        with self.assertRaises(ValidationError):
            s.save()

    def test_report_dimanche_refuse(self):
        s = nouvelle(self.m)
        s.statut, s.date_report = 'Reportée', date(2026, 10, 11)
        s.heure_debut_report, s.heure_fin_report = time(9, 0), time(11, 0)
        with self.assertRaises(ValidationError):
            s.save()

    def test_report_hors_periode_refuse(self):
        s = nouvelle(self.m)
        s.statut, s.date_report = 'Reportée', date(2027, 3, 1)
        s.heure_debut_report, s.heure_fin_report = time(9, 0), time(11, 0)
        with self.assertRaises(ValidationError):
            s.save()
