"""Non-régression des constats de la relecture finale de la phase 6."""
from datetime import date, timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings

from finance import paiements
from logistique import affectations
from logistique.models import AffectationTransport
from logistique.tests.fabriques import bus, chauffeur, trajet
from logistique.tests.test_api import Base

AUJ = date.today()


def affecter(b, c, t, debut, fin=None):
    return AffectationTransport.objects.create(bus=b, chauffeur=c, trajet=t, date_debut=debut, date_fin=fin)


class RegleDeCreationSeulementTests(TestCase):
    """I-1 : une affectation en cours se termine même si le chauffeur a changé de fonction ou de contrat."""

    def setUp(self):
        self.b, self.t, self.c = bus('01'), trajet(), chauffeur()
        self.a = affecter(self.b, self.c, self.t, AUJ - timedelta(days=10))

    def test_fonction_changee(self):
        self.c.fonction = 'gardien'
        self.c.save()
        affectations.changer_statut(self.b, 'maintenance')
        self.a.refresh_from_db()
        self.assertEqual(self.a.date_fin, AUJ)

    def test_contrat_raccourci(self):
        contrat = self.c.personne.contrats.get()
        contrat.date_fin = AUJ - timedelta(days=11)
        contrat.date_debut = AUJ - timedelta(days=400)
        contrat.save()
        affectations.terminer(self.a)
        self.a.refresh_from_db()
        self.assertEqual(self.a.date_fin, AUJ)


class AffectationsAVenirTests(TestCase):
    """I-2 : une affectation pas encore commencée est annulée (maintenance) ou annulable."""

    def setUp(self):
        self.b, self.t, self.c = bus('01'), trajet(), chauffeur()
        self.a = affecter(self.b, self.c, self.t, AUJ + timedelta(days=5))

    def test_maintenance_annule_l_affectation_future(self):
        _, terminees = affectations.changer_statut(self.b, 'maintenance')
        self.assertEqual(len(terminees), 1)
        self.assertFalse(AffectationTransport.objects.filter(pk=self.a.pk).exists())

    def test_terminer_refuse_annuler_accepte(self):
        with self.assertRaises(ValidationError) as ctx:
            affectations.terminer(self.a)
        self.assertIn('annul', str(ctx.exception))
        affectations.annuler(self.a)
        self.assertFalse(AffectationTransport.objects.filter(pk=self.a.pk).exists())

    def test_annuler_une_affectation_commencee_refuse(self):
        commencee = affecter(bus('02'), chauffeur('Malonga'), self.t, AUJ - timedelta(days=3))
        with self.assertRaises(ValidationError):
            affectations.annuler(commencee)

    def test_chauffeur_avec_affectation_future_non_disponible(self):
        self.assertNotIn(self.c, list(affectations.chauffeurs_disponibles(AUJ)))


class HistoireFigeeTests(TestCase):
    """Mineur remonté : « terminer » ne réécrit pas la fin d'une affectation déjà terminée."""

    def test_deja_terminee(self):
        a = affecter(bus('01'), chauffeur(), trajet(), AUJ - timedelta(days=60), AUJ - timedelta(days=30))
        with self.assertRaises(ValidationError):
            affectations.terminer(a)
        a.refresh_from_db()
        self.assertEqual(a.date_fin, AUJ - timedelta(days=30))


class AnnulerAPITests(Base):
    def test_annuler_via_l_api(self):
        a = affecter(self.b, self.c, self.t, AUJ + timedelta(days=3))
        self.assertEqual(self.util.post(f'/api/logistique/affectations/{a.pk}/annuler/').status_code, 403)
        r = self.resp.post(f'/api/logistique/affectations/{a.pk}/annuler/')
        self.assertEqual(r.status_code, 204)
        lignes = self.resp.get('/api/logistique/affectations/').data['results']
        self.assertEqual(lignes, [])


class DatesHistoriquesTests(TestCase):
    """I-3 : les seeds écrivent leurs dates de 2026 même des années plus tard ; la saisie, elle, reste bornée."""

    def test_saisie_bornee_mais_historique_autorise(self):
        from scolarite.tests.fabriques import Monde, inscrit
        from finance.tests.fabriques import tarif
        m = Monde()
        tarif(m.annee, m.l1.parcours)
        d = inscrit(m.l1).frais
        with mock.patch('finance.journal.timezone.localdate', return_value=date(2028, 9, 2)):
            with self.assertRaises(ValidationError):
                paiements.encaisser(d, '1000', 'especes', date=date(2026, 10, 10))
            paiements.encaisser(d, '1000', 'especes', date=date(2026, 10, 10), historique=True)

    @override_settings(DEBUG=True)
    def test_seed_demo_en_2028(self):
        with mock.patch('django.utils.timezone.localdate', return_value=date(2028, 9, 2)):
            call_command('seed_demo', verbosity=0)
        self.assertTrue(AffectationTransport.objects.exists())
