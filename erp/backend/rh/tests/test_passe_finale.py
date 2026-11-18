"""Passe finale (phase 6) : défauts reportés des RH."""
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from edt.tests.fabriques import affectation, seance_brute
from rh import vacations
from rh.contrats import contrats_a_echeance
from rh.models import Contrat
from rh.tests.fabriques import employe, permanent, vacataire
from rh.tests.test_api import Base

AUJ = date.today()


class EcheancesTests(TestCase):
    def test_contrat_renouvele_hors_echeance(self):
        g = employe('Gardien')
        c = permanent(g.personne, debut=AUJ - timedelta(days=300), fin=AUJ + timedelta(days=10))
        self.assertEqual(list(contrats_a_echeance(30)), [c])
        permanent(g.personne, debut=AUJ + timedelta(days=11), fin=None)
        self.assertEqual(list(contrats_a_echeance(30)), [])


class TableauSansContratTests(Base):
    def test_personnes_sans_aucun_contrat_comptees(self):
        employe('Nouveau')                                            # aucun contrat
        g = employe('Renouvele')
        permanent(g.personne, debut=AUJ - timedelta(days=300), fin=AUJ - timedelta(days=1))
        permanent(g.personne, debut=AUJ + timedelta(days=5))         # à venir : pas « sans contrat »
        d = self.lecteur.get('/api/rh/tableau-de-bord/').data
        # ens et ens2 du Monde n'ont aucun contrat non plus.
        self.assertEqual(d['personnes_sans_contrat_en_cours'], 3)


class ContratsTests(Base):
    def test_annuler_un_contrat_a_venir(self):
        futur = permanent(employe('Futur').personne, debut=AUJ + timedelta(days=20))
        en_cours = permanent(employe('Actuel').personne, debut=AUJ - timedelta(days=20))
        self.assertEqual(self.lecteur.delete(f'/api/rh/contrats/{futur.pk}/').status_code, 403)
        self.assertEqual(self.resp.delete(f'/api/rh/contrats/{en_cours.pk}/').status_code, 400)
        self.assertEqual(self.resp.delete(f'/api/rh/contrats/{futur.pk}/').status_code, 204)
        self.assertFalse(Contrat.objects.filter(pk=futur.pk).exists())

    def test_contrat_avec_vacations_fige(self):
        c = vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=60), fin=AUJ + timedelta(days=200))
        a = affectation(self.m.algo, self.m.l1, self.m.ens, 2)
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=AUJ - timedelta(days=3))
        vacations.confirmer(a)
        r = self.resp.patch(f'/api/rh/contrats/{c.pk}/', {'type': 'permanent', 'salaire_mensuel': '500000'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.resp.patch(f'/api/rh/contrats/{c.pk}/', {'personne': self.m.ens2.pk}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.resp.patch(f'/api/rh/contrats/{c.pk}/', {'diplome': 'Doctorat'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)


class RetraitConcurrentTests(Base):
    def test_double_retrait_avec_objet_perime(self):
        vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=60), fin=AUJ + timedelta(days=200))
        a = affectation(self.m.algo, self.m.l1, self.m.ens, 2)
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=AUJ - timedelta(days=3))
        v = vacations.confirmer(a)
        perime = vacations.Vacation.objects.get(pk=v.pk)
        vacations.retirer(v, motif='x')
        with self.assertRaises(ValidationError):
            vacations.retirer(perime, motif='encore')
