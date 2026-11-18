"""Non-régression des constats de la relecture finale de la phase 2."""
from datetime import date, time

from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import AnneeAcademique, Classe
from core.tests import fabriques as f
from edt.models import AffectationEC, Seance
from edt.tests.fabriques import affectation, enseignant
from edt.tests.test_api import LUNDI, Base


def publiee(ec, classe, ens, jour=LUNDI, debut=time(9, 0), fin=time(11, 0), **kw):
    return Seance.objects.create(ec=ec, classe=classe, enseignant=ens, date_seance=jour, heure_debut=debut,
                                 heure_fin=fin, type_seance='CM', statut='Confirmée', **kw)


class SeanceLieeHorsPerimetreTests(Base):
    """Critical 1 : seance_liee ne permet pas de sortir du périmètre."""

    def setUp(self):
        super().setUp()
        self.math = publiee(self.ec_math, self.l2_math, self.matheux)
        affectation(self.m.bdd, self.m.l2, self.matheux, 10, hors_departement=True)

    def test_lier_a_une_seance_hors_perimetre_refuse(self):
        r = self.chef.post('/api/edt/seances/', self.donnees(enseignant=self.matheux.pk, seance_liee=self.math.pk),
                           format='json')
        self.assertEqual(r.status_code, 403)

    def test_seances_liees_ne_revele_pas_le_hors_perimetre(self):
        a = publiee(self.m.bdd, self.m.l2, self.matheux, jour=date(2026, 10, 6))
        Seance.objects.filter(pk=self.math.pk).update(seance_liee=a)
        r = self.chef.get(f'/api/edt/seances/{a.pk}/seances_liees/')
        self.assertEqual(r.data['count'], 0)


class ReportVisibleDansLaBonneSemaineTests(Base):
    """Important 1 / Minor 1 : une séance reportée apparaît dans la semaine de son report."""

    def setUp(self):
        super().setUp()
        s = publiee(self.m.bdd, self.m.l2, self.m.ens2)
        s.statut, s.date_report = 'Reportée', date(2026, 10, 13)
        s.heure_debut_report, s.heure_fin_report = time(9, 0), time(11, 0)
        s.save()

    def test_liste_gestionnaire(self):
        self.assertEqual(self.resp.get('/api/edt/seances/?date_debut=2026-10-12&date_fin=2026-10-17').data['count'], 1)
        self.assertEqual(self.resp.get('/api/edt/seances/?date_debut=2026-10-05&date_fin=2026-10-10').data['count'], 0)

    def test_planning_personnel(self):
        self.assertEqual(len(self.prof.get('/api/edt/moi/planning/?date_debut=2026-10-12&date_fin=2026-10-17').data), 1)
        self.assertEqual(len(self.prof.get('/api/edt/moi/planning/?date_debut=2026-10-05&date_fin=2026-10-10').data), 0)
        # Reportée plus loin (31/10) : n'apparaît pas dans une semaine intermédiaire.
        Seance.objects.update(date_report=date(2026, 10, 31))
        self.assertEqual(len(self.prof.get('/api/edt/moi/planning/?date_debut=2026-10-12&date_fin=2026-10-17').data), 0)


class PaireMutualiseeTests(Base):
    """Important 2 : déplacer ou reporter une séance mutualisée entraîne sa jumelle."""

    def setUp(self):
        super().setUp()
        self.bcg = Classe.objects.create(annee=self.m.annee, parcours=f.parcours('Licence', 1),
                                         portail=f.portail(self.m.fac, 'BCG'))
        ec_bcg = f.ec(f.ue('UE-BCG', 'S1', port=self.bcg.portail), 'ALGO-BCG', credits=2, dep=self.m.dep)
        self.a = publiee(self.m.algo, self.m.l1, self.m.ens2)
        self.b = publiee(ec_bcg, self.bcg, self.m.ens2, seance_liee=self.a)

    def test_deplacer_entraine_la_jumelle(self):
        r = self.resp.patch(f'/api/edt/seances/{self.a.pk}/', {'date_seance': '2026-10-06'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.b.refresh_from_db()
        self.assertEqual(self.b.date_seance, date(2026, 10, 6))

    def test_reporter_entraine_la_jumelle(self):
        r = self.resp.patch(f'/api/edt/seances/{self.b.pk}/reporter/', {
            'date_report': '2026-10-07', 'heure_debut_report': '14:15', 'heure_fin_report': '16:15'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.a.refresh_from_db()
        self.assertEqual((self.a.statut, self.a.date_report), ('Reportée', date(2026, 10, 7)))


class AnneeArchiveeFigeeTests(Base):
    """Important 4 : rien ne bouge sur une année archivée."""

    def test_suppression_et_affectation_refusees(self):
        s = publiee(self.m.bdd, self.m.l2, self.m.ens2, jour=date(2026, 10, 5))
        AnneeAcademique.objects.filter(pk=self.m.annee.pk).update(statut='archivee', en_cours=False)
        self.assertEqual(self.resp.delete(f'/api/edt/seances/{s.pk}/').status_code, 400)
        r = self.resp.post('/api/edt/affectations/', {'ec': self.m.bdd.pk, 'classe': self.m.l2.pk,
                                                      'enseignant': self.m.ens2.pk, 'heures_prevues': 10}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Seance.objects.filter(pk=s.pk).exists())


class StatutsReportTests(Base):
    """Minor 2 re-gradé : un brouillon ne peut pas être reporté ; une séance reportée peut être annulée."""

    def test_reporter_un_brouillon_refuse(self):
        sid = self.chef.post('/api/edt/seances/', self.donnees(), format='json').data['id']
        r = self.chef.patch(f'/api/edt/seances/{sid}/reporter/', {
            'date_report': '2026-10-06', 'heure_debut_report': '09:00', 'heure_fin_report': '11:00'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_annuler_une_seance_reportee(self):
        s = publiee(self.m.bdd, self.m.l2, self.m.ens2)
        self.chef.patch(f'/api/edt/seances/{s.pk}/reporter/', {
            'date_report': '2026-10-06', 'heure_debut_report': '09:00', 'heure_fin_report': '11:00'}, format='json')
        r = self.chef.patch(f'/api/edt/seances/{s.pk}/', {'statut': 'Annulée'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)


class RequetesBorneesTests(Base):
    """Important 3 : le nombre de requêtes ne grandit pas avec le nombre de lignes."""

    def compter(self, url):
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self.resp.get(url).status_code, 200)
        return len(ctx)

    def test_enseignements_et_affectations(self):
        affectation(self.m.bdd, self.m.l2, self.m.ens2, 10)
        publiee(self.m.bdd, self.m.l2, self.m.ens2)
        self.compter('/api/edt/enseignements/')  # premier appel : mises en cache ponctuelles
        avant = (self.compter('/api/edt/enseignements/'), self.compter('/api/edt/affectations/'))
        for i in range(4):
            ens = enseignant(f'Prof{"abcd"[i]}', self.m.dep)
            affectation(self.m.bdd, self.m.l2, ens, 5)
            affectation(self.m.algo, self.m.l1, ens, 5)
            publiee(self.m.bdd, self.m.l2, ens, jour=date(2026, 10, 6 + i))
        apres = (self.compter('/api/edt/enseignements/'), self.compter('/api/edt/affectations/'))
        self.assertEqual(apres, avant)
        self.assertEqual(AffectationEC.objects.count(), 9)
