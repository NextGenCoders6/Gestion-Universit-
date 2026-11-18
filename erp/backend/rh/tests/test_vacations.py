from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase

from core.models import Classe
from core.tests import fabriques as f
from edt.tests.fabriques import Monde, affectation, seance_brute
from rh import vacations
from rh.models import HistoriqueVacation, Vacation
from rh.tests.fabriques import permanent, vacataire

AUJ = date.today()
PASSE = AUJ - timedelta(days=14)
FUTUR = AUJ + timedelta(days=14)


class Base(TestCase):
    def setUp(self):
        self.m = Monde()
        self.ens = self.m.ens
        self.contrat = vacataire(self.ens.personne, debut=AUJ - timedelta(days=90), fin=AUJ + timedelta(days=200))
        self.aff = affectation(self.m.algo, self.m.l1, self.ens, 4)

    def seance(self, jour, debut=time(9, 0), fin=time(11, 0), classe=None, ec=None, **kw):
        return seance_brute(ec or self.m.algo, classe or self.m.l1, self.ens, jour=jour, debut=debut, fin=fin, **kw)


class EtatTests(Base):
    def test_terminee(self):
        self.seance(PASSE)
        self.seance(PASSE - timedelta(days=1))
        e = vacations.etat(self.aff)
        self.assertEqual((e['heures_effectuees'], e['heures_dues'], e['terminee']), (4.0, 4.0, True))
        self.assertTrue(e['confirmable'])
        self.assertEqual(e['contrat'], self.contrat)

    def test_non_terminee_et_brouillons_ignores(self):
        self.seance(PASSE)
        self.seance(FUTUR)
        self.seance(PASSE - timedelta(days=1), statut='brouillon')
        e = vacations.etat(self.aff)
        self.assertEqual((e['heures_effectuees'], e['terminee']), (2.0, False))

    def test_sans_contrat_de_vacataire(self):
        self.contrat.delete()
        permanent(self.ens.personne, debut=AUJ - timedelta(days=10))
        e = vacations.etat(self.aff)
        self.assertFalse(e['confirmable'])
        self.assertIn('contrat de vacataire', e['motif_blocage'])

    def test_mutualisee_payee_une_fois(self):
        bcg = Classe.objects.create(annee=self.m.annee, parcours=f.parcours('Licence', 1),
                                    portail=f.portail(self.m.fac, 'BCG'))
        ec_bcg = f.ec(f.ue('UE-BCG', 'S1', port=bcg.portail), 'ALGO-BCG', credits=2, dep=self.m.dep)
        aff_bcg = affectation(ec_bcg, bcg, self.ens, 2)
        a = self.seance(PASSE)
        self.seance(PASSE, classe=bcg, ec=ec_bcg, seance_liee=a)
        e = vacations.etat(aff_bcg)
        self.assertEqual((e['heures_effectuees'], e['heures_jumelles'], e['heures_dues'], e['terminee']),
                         (2.0, 2.0, 0.0, True))
        self.assertEqual(vacations.etat(self.aff)['heures_dues'], 2.0)


class ConfirmationTests(Base):
    def setUp(self):
        super().setUp()
        self.seance(PASSE)
        self.seance(PASSE - timedelta(days=1))
        self.jury = User.objects.create_user('fac')

    def test_par_defaut(self):
        appels = []
        vacations.APRES_CONFIRMATION.append(appels.append)
        try:
            v = vacations.confirmer(self.aff, par=self.jury)
        finally:
            vacations.APRES_CONFIRMATION.remove(appels.append)
        self.assertEqual((v.heures_retenues, v.taux_horaire, v.montant), (Decimal('4'), Decimal('5000'), Decimal('20000')))
        self.assertEqual((v.contrat, v.confirmee_par), (self.contrat, self.jury))
        self.assertEqual(appels, [v])
        h = HistoriqueVacation.objects.get()
        self.assertEqual((h.action, h.heures_retenues, h.montant), ('confirmation', Decimal('4'), Decimal('20000')))

    def test_taux_fige(self):
        v = vacations.confirmer(self.aff)
        self.contrat.taux_horaire = Decimal('9000')
        self.contrat.save()
        v.refresh_from_db()
        self.assertEqual(v.montant, Decimal('20000'))

    def test_motif_si_heures_modifiees(self):
        with self.assertRaises(ValidationError) as ctx:
            vacations.confirmer(self.aff, heures_retenues=3)
        self.assertIn('motif', ctx.exception.message_dict)
        v = vacations.confirmer(self.aff, heures_retenues='3.5', motif='Une séance écourtée')
        self.assertEqual(v.montant, Decimal('17500'))

    def test_heures_negatives(self):
        with self.assertRaises(ValidationError) as ctx:
            vacations.confirmer(self.aff, heures_retenues=-1, motif='x')
        self.assertIn('heures_retenues', ctx.exception.message_dict)

    def test_double_confirmation(self):
        vacations.confirmer(self.aff)
        with self.assertRaises(ValidationError):
            vacations.confirmer(self.aff)
        self.assertEqual(Vacation.objects.count(), 1)

    def test_contrat_expire(self):
        self.contrat.date_fin = AUJ - timedelta(days=1)
        self.contrat.save()
        with self.assertRaises(ValidationError) as ctx:
            vacations.confirmer(self.aff)
        self.assertIn('contrat de vacataire', str(ctx.exception))

    def test_suppression_affectation_confirmee_refusee(self):
        vacations.confirmer(self.aff)
        with self.assertRaises(ProtectedError):
            self.aff.delete()


class NonTermineeTests(Base):
    def test_motif_obligatoire(self):
        self.seance(PASSE)
        with self.assertRaises(ValidationError) as ctx:
            vacations.confirmer(self.aff)
        self.assertIn('motif', ctx.exception.message_dict)
        v = vacations.confirmer(self.aff, motif='Module arrêté : enseignant parti')
        self.assertEqual(v.heures_retenues, Decimal('2'))


class RetraitTests(Base):
    def setUp(self):
        super().setUp()
        self.seance(PASSE)
        self.seance(PASSE - timedelta(days=1))
        self.v = vacations.confirmer(self.aff)

    def test_retrait(self):
        with self.assertRaises(ValidationError):
            vacations.retirer(self.v, motif='')
        vacations.retirer(self.v, motif='Heures mal comptées')
        self.assertFalse(Vacation.objects.exists())
        self.assertEqual(list(HistoriqueVacation.objects.order_by('le', 'pk').values_list('action', flat=True)),
                         ['confirmation', 'retrait'])

    def test_retrait_refuse_par_une_verification(self):
        def payee(vacation):
            raise ValidationError('La vacation est déjà payée.')
        vacations.VERIFICATIONS_RETRAIT.append(payee)
        try:
            with self.assertRaises(ValidationError):
                vacations.retirer(self.v, motif='x')
        finally:
            vacations.VERIFICATIONS_RETRAIT.remove(payee)
        self.assertTrue(Vacation.objects.exists())
