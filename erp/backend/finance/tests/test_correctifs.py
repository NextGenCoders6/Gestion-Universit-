"""Non-régression des constats de la relecture finale de la phase 5."""
from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.droits import definir_droits
from finance import frais, paiements
from finance.models import FraisScolarite, Paie
from finance.tests.fabriques import tarif
from rh.tests.fabriques import employe, permanent
from scolarite.tests.fabriques import Monde, inscrit

D = Decimal


def client(nom, groupes):
    u = User.objects.create_user(nom, password='x')
    definir_droits(u, list(groupes))
    c = APIClient()
    c.force_authenticate(u)
    return c


class TarifSurEcheancierAdapteTests(TestCase):
    """I-1 : un tarif modifié garde la somme des mensualités égale au montant dû, même adaptées."""

    def test_baisse_puis_paiement_complet(self):
        m = Monde()
        t = tarif(m.annee, m.l1.parcours, '1500000')
        d = inscrit(m.l1).frais
        frais.adapter_echeancier(d, [('2026-10', date(2026, 11, 5), D('500000')), ('2026-11', date(2026, 12, 5), D('1000000'))])
        t.montant = D('1000000')
        t.save()
        d.refresh_from_db()
        self.assertEqual(sum(e.montant for e in d.echeances.all()), D('1000000'))
        self.assertEqual([e.date_limite for e in d.echeances.all()], [date(2026, 11, 5), date(2026, 12, 5)])
        paiements.encaisser(d, '1000000', 'especes', date=date(2026, 11, 1))
        d.refresh_from_db()
        self.assertFalse(frais.en_retard(d, jour=date(2027, 9, 1)))

    def test_ajuster_un_echeancier_adapte_garde_les_proportions(self):
        m = Monde()
        tarif(m.annee, m.l1.parcours, '1500000')
        d = inscrit(m.l1).frais
        frais.adapter_echeancier(d, [('2026-10', date(2026, 11, 5), D('500000')), ('2026-11', date(2026, 12, 5), D('1000000'))])
        frais.ajuster(d, D('3000000'))
        self.assertEqual([e.montant for e in d.echeances.all()], [D('1000000'), D('2000000')])


class TableauSansAnnulationsTests(TestCase):
    """I-3 : un paiement annulé ne compte ni en recette ni en dépense."""

    def test_annulation_neutre(self):
        m = Monde()
        tarif(m.annee, m.l1.parcours)
        d = inscrit(m.l1).frais
        p = paiements.encaisser(d, '100000', 'especes')
        paiements.annuler_paiement(p, 'Erreur')
        data = client('fin', ['finance_utilisateur']).get(f'/api/finance/tableau-de-bord/?annee={m.annee.pk}').data
        self.assertEqual((data['recettes'], data['depenses'], data['solde']), (0.0, 0.0, 0.0))
        self.assertEqual(data['tresorerie'][-1], {'mois': data['tresorerie'][-1]['mois'], 'recettes': 0.0, 'depenses': 0.0})


class ChangementDeClasseTests(TestCase):
    """I-4 : changer de niveau dans l'année recalcule le dossier de frais."""

    def test_l1_vers_l2(self):
        m = Monde()
        tarif(m.annee, m.l1.parcours, '300000')
        tarif(m.annee, m.l2.parcours, '900000')
        i = inscrit(m.l1)
        r = client('sec', ['scolarite_secretariat']).patch(f'/api/scolarite/inscriptions/{i.pk}/', {'classe': m.l2.pk},
                                                           format='json')
        self.assertEqual(r.status_code, 200, r.data)
        d = FraisScolarite.objects.get(inscription=i)
        self.assertEqual(d.montant_du, D('900000'))
        self.assertEqual(sum(e.montant for e in d.echeances.all()), D('900000'))


class EcheancierInvalideTests(TestCase):
    """I-5 : un échéancier mal formé donne 400, jamais 500."""

    def test_entrees_invalides(self):
        m = Monde()
        tarif(m.annee, m.l1.parcours, '1000000')
        d = inscrit(m.l1).frais
        resp = client('resp', ['finance_responsable'])
        url = f'/api/finance/frais/{d.pk}/echeancier/'
        for lignes in ([{'mois': '2026-10', 'date_limite': '', 'montant': '1000000'}],
                       [{'mois': 'xxxxxxxxxxxxx', 'date_limite': '2026-11-05', 'montant': '1000000'}],
                       [{'mois': '2026-10', 'date_limite': '2026-11-05'}]):
            with self.subTest(lignes=lignes):
                self.assertEqual(resp.put(url, {'echeances': lignes}, format='json').status_code, 400)
        self.assertEqual(d.echeances.count(), 10)


class PaieDuMoisAvecVacationsTests(TestCase):
    """I-6 : la liste d'un mois montre ses salaires et toutes les vacations."""

    def test_filtre(self):
        from edt.tests.fabriques import Monde as MondeEdt, affectation, seance_brute
        from rh import vacations
        from rh.tests.fabriques import vacataire
        from datetime import timedelta
        m = MondeEdt()
        g = employe('Gardien')
        permanent(g.personne, debut=date(2026, 1, 1), salaire='120000')
        from finance import paie
        paie.generer_salaires('2026-09')
        paie.generer_salaires('2026-10')
        auj = date.today()
        vacataire(m.ens.personne, debut=auj - timedelta(days=60), fin=auj + timedelta(days=200))
        a = affectation(m.algo, m.l1, m.ens, 2)
        seance_brute(m.algo, m.l1, m.ens, jour=auj - timedelta(days=3))
        vacations.confirmer(a)
        lignes = client('fin', ['finance_utilisateur']).get('/api/finance/paie/?mois=2026-10&avec_vacations=true').data
        self.assertEqual(sorted((l['origine'], l['mois']) for l in lignes['results']),
                         [('salaire', '2026-10'), ('vacation', None)])
        self.assertEqual(Paie.objects.count(), 3)


class SeedEtudiantAJourTests(TestCase):
    """I-2 : le compte de démonstration est à jour quelle que soit la date du seed."""

    @override_settings(DEBUG=True)
    def test_a_jour_en_mars(self):
        with mock.patch('django.utils.timezone.localdate', return_value=date(2027, 3, 1)):
            for commande in ('seed_socle', 'seed_edt', 'seed_scolarite', 'seed_rh', 'seed_finance'):
                call_command(commande, verbosity=0)
        d = User.objects.get(username='etudiant').personne.etudiant.inscriptions.get().frais
        self.assertFalse(frais.en_retard(d, jour=date(2027, 3, 1)))
