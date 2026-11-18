from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.tests import fabriques as f
from edt import quotas
from edt.tests.fabriques import Monde, seance_brute


class QuotasECTests(TestCase):
    def setUp(self):
        self.m = Monde()

    def test_heures_max_derivent_des_credits(self):
        self.assertEqual(quotas.heures_max(self.m.algo), 24)
        self.assertEqual(quotas.heures_restantes(self.m.algo, self.m.l1), 24)

    def test_seuls_confirmee_et_reportee_comptent(self):
        for statut in ('brouillon', 'Annulée', 'Confirmée'):
            seance_brute(self.m.algo, self.m.l1, self.m.ens, statut=statut)
        self.assertEqual(quotas.heures_consommees(self.m.algo, self.m.l1), 2)

    def test_agrege_tous_les_enseignants(self):
        seance_brute(self.m.algo, self.m.l1, self.m.ens)
        seance_brute(self.m.algo, self.m.l1, self.m.ens2, jour=date(2026, 10, 6))
        self.assertEqual(quotas.heures_consommees(self.m.algo, self.m.l1), 4)
        self.assertEqual(quotas.heures_consommees(self.m.algo, self.m.l1, enseignant=self.m.ens), 2)

    def test_heures_comptees_par_classe(self):
        autre = f.portail(self.m.fac, 'BCG')
        from core.models import Classe
        l1_bcg = Classe.objects.create(annee=self.m.annee, parcours=f.parcours('Licence', 1), portail=autre)
        seance_brute(self.m.algo, self.m.l1, self.m.ens)
        self.assertEqual(quotas.heures_consommees(self.m.algo, l1_bcg), 0)
        self.assertEqual(quotas.heures_consommees(self.m.algo, self.m.l1), 2)

    def test_cours_mutualise_compte_dans_chaque_classe(self):
        """Mutualisé = une séance par classe : chacune pèse sur le quota de sa classe."""
        from core.models import Classe
        from edt.models import Seance
        bcg = Classe.objects.create(annee=self.m.annee, parcours=f.parcours('Licence', 1),
                                    portail=f.portail(self.m.fac, 'BCG'))
        ec_bcg = f.ec(f.ue('UE-BCG', 'S1', port=bcg.portail), 'ALGO-BCG', credits=2, dep=self.m.dep)
        a = seance_brute(self.m.algo, self.m.l1, self.m.ens)
        b = seance_brute(ec_bcg, bcg, self.m.ens)
        Seance.objects.filter(pk=b.pk).update(seance_liee=a)
        self.assertEqual(quotas.heures_consommees(self.m.algo, self.m.l1), 2)
        self.assertEqual(quotas.heures_consommees(ec_bcg, bcg), 2)

    def test_pause_deduite_et_creneau_de_report_prioritaire(self):
        seance_brute(self.m.algo, self.m.l1, self.m.ens, debut=time(9, 0), fin=time(12, 15))  # 3 h
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=date(2026, 10, 6), statut='Reportée',
                     date_report=date(2026, 10, 7), heure_debut_report=time(13, 0), heure_fin_report=time(14, 0))
        self.assertEqual(quotas.heures_consommees(self.m.algo, self.m.l1), 4)

    def test_heures_effectuees_suit_la_date_de_report(self):
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=date(2020, 1, 6))
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=date(2020, 1, 7), statut='Reportée',
                     date_report=date(2099, 1, 8), heure_debut_report=time(9, 0), heure_fin_report=time(10, 0))
        self.assertEqual(quotas.heures_effectuees(self.m.algo, self.m.l1), 2)

    def test_exclure_neutralise_la_seance_modifiee(self):
        s = seance_brute(self.m.algo, self.m.l1, self.m.ens)
        self.assertEqual(quotas.heures_consommees(self.m.algo, self.m.l1, exclure=s.pk), 0)

    def test_par_type(self):
        seance_brute(self.m.algo, self.m.l1, self.m.ens, type_seance='TD')
        self.assertEqual(quotas.heures_consommees(self.m.algo, self.m.l1, type_seance='CM'), 0)
        self.assertEqual(quotas.heures_consommees(self.m.algo, self.m.l1, type_seance='TD'), 2)

    def test_plafond_type(self):
        ec = self.m.bdd
        ec.heures_cm, ec.heures_td, ec.heures_tp = 12, 0, 6
        ec.save()
        self.assertEqual(quotas.plafond_type(ec, 'CM'), 12)
        self.assertIsNone(quotas.plafond_type(ec, 'TD'))  # 0 = non ventilé


class VentilationECTests(TestCase):
    def test_ec_ventilation_depasse_refusee(self):
        m = Monde()
        ec = m.algo  # 2 crédits = 24 h
        ec.heures_cm, ec.heures_td, ec.heures_tp = 12, 10, 4
        with self.assertRaises(ValidationError):
            ec.save()
        ec.heures_tp = 2
        ec.save()
