from datetime import date, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from logistique import affectations
from logistique.models import AffectationTransport, Bus, Trajet
from logistique.tests.fabriques import bus, chauffeur, trajet
from rh.tests.fabriques import employe, permanent

J = date(2026, 11, 2)


def affecter(b, c, t, debut=J, fin=None):
    return AffectationTransport.objects.create(bus=b, chauffeur=c, trajet=t, date_debut=debut, date_fin=fin)


class BusEtTrajetTests(TestCase):
    def test_unicite_et_capacite(self):
        bus('01')
        with self.assertRaises(ValidationError):
            bus('01')
        with self.assertRaises(ValidationError):
            Bus.objects.create(numero='02', plaque='CG-01-AA', capacite=40)
        with self.assertRaises(ValidationError):
            Bus.objects.create(numero='03', plaque='CG-03-AA', capacite=0)

    def test_heures_du_trajet(self):
        with self.assertRaises(ValidationError) as ctx:
            Trajet.objects.create(nom='T', depart='A', destination='B', heure_depart=time(8), heure_arrivee=time(7))
        self.assertIn('heure_arrivee', ctx.exception.message_dict)


class AffectationTests(TestCase):
    def setUp(self):
        self.b, self.t, self.c = bus('01'), trajet(), chauffeur()

    def test_non_chauffeur_refuse(self):
        g = employe('Gardien', 'gardien')
        permanent(g.personne, debut=date(2025, 1, 1))
        with self.assertRaises(ValidationError) as ctx:
            affecter(self.b, g, self.t)
        self.assertIn('chauffeur', ctx.exception.message_dict)

    def test_contrat_absent_ou_fini(self):
        sans = employe('Sans', 'chauffeur')
        with self.assertRaises(ValidationError):
            affecter(self.b, sans, self.t)
        fini = chauffeur('Fini', debut=date(2024, 1, 1), fin=date(2026, 10, 31))
        with self.assertRaises(ValidationError) as ctx:
            affecter(self.b, fini, self.t)
        self.assertIn('contrat', str(ctx.exception))

    def test_bus_non_actif(self):
        b = bus('02', statut='maintenance')
        with self.assertRaises(ValidationError) as ctx:
            affecter(b, self.c, self.t)
        self.assertIn('bus', ctx.exception.message_dict)

    def test_chevauchements(self):
        affecter(self.b, self.c, self.t, debut=J)
        autre = chauffeur('Malonga')
        with self.assertRaises(ValidationError) as ctx:
            affecter(self.b, autre, self.t, debut=date(2026, 12, 1))   # même bus, première affectation sans fin
        self.assertIn('bus', ctx.exception.message_dict)
        b2 = bus('02')
        with self.assertRaises(ValidationError) as ctx:
            affecter(b2, self.c, self.t, debut=date(2026, 12, 1))       # même chauffeur
        self.assertIn('chauffeur', ctx.exception.message_dict)

    def test_contigu_apres_fin(self):
        a = affecter(self.b, self.c, self.t, debut=J)
        affectations.terminer(a, date(2026, 11, 30))
        a.refresh_from_db()
        self.assertEqual(a.date_fin, date(2026, 11, 30))
        affecter(self.b, chauffeur('Malonga'), self.t, debut=date(2026, 12, 1))
        self.assertTrue(a.est_active(date(2026, 11, 30)))
        self.assertFalse(a.est_active(date(2026, 12, 1)))

    def test_fin_avant_debut(self):
        a = affecter(self.b, self.c, self.t, debut=J)
        with self.assertRaises(ValidationError):
            affectations.terminer(a, date(2026, 11, 1))


class StatutEtDisponibiliteTests(TestCase):
    def setUp(self):
        self.b, self.t, self.c = bus('01'), trajet(), chauffeur()
        self.a = affecter(self.b, self.c, self.t)

    def test_maintenance_termine_l_affectation(self):
        u = User.objects.create_user('log')
        affectations.changer_statut(self.b, 'maintenance', jour=date(2026, 11, 20), par=u)
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual((self.b.statut, self.a.date_fin), ('maintenance', date(2026, 11, 20)))
        with self.assertRaises(ValidationError):
            affectations.changer_statut(self.b, 'roulant')

    def test_chauffeurs_disponibles(self):
        libre = chauffeur('Malonga')
        self.assertEqual(list(affectations.chauffeurs_disponibles(date(2026, 11, 20))), [libre])
        affectations.terminer(self.a, date(2026, 11, 20))
        self.assertEqual(set(affectations.chauffeurs_disponibles(date(2026, 11, 21))), {libre, self.c})

    def test_alertes(self):
        self.assertEqual(affectations.alertes(date(2026, 11, 20)), [])
        contrat = self.c.personne.contrats.get()
        contrat.date_fin = date(2026, 11, 15)
        contrat.save()
        alertes = affectations.alertes(date(2026, 11, 20))
        self.assertEqual([a['affectation'] for a in alertes], [self.a.pk])
        self.assertIn('contrat', alertes[0]['message'])
