"""Résumé Finance du launchpad : taux de recouvrement des frais de l'année en cours."""
from core.tests import fabriques as f
from finance import paiements
from finance.tests.test_api import Base

URL = '/api/core/lanceur/'


def tuile(c):
    return next(e for e in c.get(URL).data if e['module'] == 'finance')


class ResumeFinanceTests(Base):
    def test_finance_taux_et_retards(self):
        paiements.encaisser(self.a, '300000', 'especes')      # attendus 3 000 000 (deux dossiers L1), encaissés 300 000
        e = tuile(self.util)
        tableau = self.util.get('/api/finance/tableau-de-bord/').data
        self.assertEqual((e['valeur'], e['unite'], e['libelle']), (10.0, '%', 'des frais encaissés'))
        retards = tableau['dossiers_en_retard']
        self.assertEqual(e['ton'], 'alerte' if retards else 'normal')
        self.assertEqual(e['detail'], 'Aucun dossier en retard' if retards == 0 else
                         f"{retards} dossier{'s' if retards > 1 else ''} en retard")

    def test_finance_sans_frais_attendus(self):
        self.m.annee.en_cours = False
        self.m.annee.save()
        f.annee('2027-2028', en_cours=True)
        e = tuile(self.util)
        self.assertEqual((e['valeur'], e['detail'], e['ton']), (None, 'Aucun frais attendu', 'normal'))

    def test_tableau_de_bord_inchange_sans_frais(self):
        self.m.annee.en_cours = False
        self.m.annee.save()
        f.annee('2027-2028', en_cours=True)
        self.assertEqual(self.util.get('/api/finance/tableau-de-bord/').data['taux_recouvrement'], 0.0)
