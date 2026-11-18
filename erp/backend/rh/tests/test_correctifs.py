"""Non-régression des constats de la relecture finale de la phase 4."""
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings

from core.models import Classe
from core.tests import fabriques as f
from edt.models import AffectationEC
from edt.tests.fabriques import Monde, affectation, seance_brute
from rh import vacations
from rh.tests.fabriques import permanent, vacataire
from rh.tests.test_api import Base as BaseAPI

AUJ = date.today()


class AffectationConfirmeeFigeeTests(TestCase):
    """I-1 : l'EDT ne modifie pas une affectation dont la vacation est confirmée."""

    def setUp(self):
        self.m = Monde()
        vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=60), fin=AUJ + timedelta(days=200))
        self.a = affectation(self.m.algo, self.m.l1, self.m.ens, 2)
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=AUJ - timedelta(days=3))
        vacations.confirmer(self.a)

    def test_modification_refusee(self):
        a = AffectationEC.objects.get(pk=self.a.pk)
        a.enseignant = self.m.ens2
        with self.assertRaises(ValidationError) as ctx:
            a.save()
        self.assertIn('retirez', str(ctx.exception))
        a = AffectationEC.objects.get(pk=self.a.pk)
        a.heures_prevues = 3
        with self.assertRaises(ValidationError):
            a.save()

    def test_enregistrement_sans_changement_et_apres_retrait(self):
        AffectationEC.objects.get(pk=self.a.pk).save()
        vacations.retirer(self.a.vacation, motif='x')
        a = AffectationEC.objects.get(pk=self.a.pk)
        a.heures_prevues = 3
        a.save()


class ContratDeLaPeriodeTests(TestCase):
    """I-2 : le contrat retenu est celui qui couvre les séances, pas celui d'aujourd'hui."""

    def setUp(self):
        self.m = Monde()
        self.a = affectation(self.m.algo, self.m.l1, self.m.ens, 2)
        seance_brute(self.m.algo, self.m.l1, self.m.ens, jour=AUJ - timedelta(days=30))

    def test_contrat_termine_depuis(self):
        ancien = vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=200), fin=AUJ - timedelta(days=10),
                           taux='5000')
        e = vacations.etat(self.a)
        self.assertTrue(e['confirmable'])
        self.assertEqual(e['contrat'], ancien)
        self.assertEqual(vacations.confirmer(self.a).montant, 10000)

    def test_renouvellement_garde_le_taux_de_la_periode(self):
        vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=200), fin=AUJ - timedelta(days=10), taux='5000')
        vacataire(self.m.ens.personne, debut=AUJ - timedelta(days=9), fin=AUJ + timedelta(days=200), taux='8000')
        self.assertEqual(vacations.confirmer(self.a).taux_horaire, 5000)


class EnseignantSansContratListeTests(BaseAPI):
    """I-3 : un enseignant sans aucun contrat apparaît, avec le motif ; un permanent non."""

    def test_liste(self):
        sans = affectation(self.m.algo, self.m.l1, self.m.ens, 2)
        permanent(self.m.ens2.personne, debut=AUJ - timedelta(days=60))
        affectation(self.m.bdd, self.m.l2, self.m.ens2, 4)
        lignes = self.lecteur.get('/api/rh/vacations/').data
        self.assertEqual([l['affectation'] for l in lignes], [sans.pk])
        self.assertIn('contrat de vacataire', lignes[0]['motif_blocage'])


class HeuresInvalidesTests(TestCase):
    """M-1 : des heures démesurées donnent une erreur de saisie, pas une erreur serveur."""

    def test_trop_grand(self):
        m = Monde()
        vacataire(m.ens.personne, debut=AUJ - timedelta(days=60), fin=AUJ + timedelta(days=200))
        a = affectation(m.algo, m.l1, m.ens, 2)
        seance_brute(m.algo, m.l1, m.ens, jour=AUJ - timedelta(days=3))
        for valeur in ('10000', '1e30'):
            with self.subTest(valeur=valeur), self.assertRaises(ValidationError) as ctx:
                vacations.confirmer(a, heures_retenues=valeur, motif='x')
            self.assertIn('heures_retenues', ctx.exception.message_dict)


class JumelleSansPrincipaleTests(TestCase):
    """M-4 : une séance jumelle n'est déduite que si sa séance principale est comptée et passée."""

    def test_principale_annulee(self):
        m = Monde()
        bcg = Classe.objects.create(annee=m.annee, parcours=f.parcours('Licence', 1), portail=f.portail(m.fac, 'BCG'))
        ec_bcg = f.ec(f.ue('UE-BCG', 'S1', port=bcg.portail), 'ALGO-BCG', credits=2, dep=m.dep)
        aff = affectation(ec_bcg, bcg, m.ens, 2)
        principale = seance_brute(m.algo, m.l1, m.ens, jour=AUJ - timedelta(days=3), statut='Annulée')
        seance_brute(ec_bcg, bcg, m.ens, jour=AUJ - timedelta(days=3), seance_liee=principale)
        self.assertEqual(vacations.etat(aff)['heures_dues'], 2.0)


@override_settings(DEBUG=True)
class SeedNeLaissePasDeNotesVidesTests(TestCase):
    """I-4 : les EC de démonstration RH ont leurs notes en L2 INFO."""

    def test_deliberation_l2_info(self):
        from scolarite.moteur import deliberation
        for commande in ('seed_socle', 'seed_edt', 'seed_scolarite', 'seed_rh'):
            call_command(commande, verbosity=0)
        l2 = Classe.objects.get(annee__libelle='2026-2027', parcours__niveau=2, filiere__code='INFO')
        manquants = {code for l in deliberation(l2, 'S3') for code in l['ecs_non_saisis']}
        self.assertFalse(manquants & {'SYSEXP', 'WEB1'})
