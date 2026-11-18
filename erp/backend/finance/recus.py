"""Reçus PDF : paiement de frais, paiement de paie, opération manuelle."""
from django.template.loader import render_to_string
from django.utils import timezone

from core.documents import logo_data_uri, rendre_pdf
from core.models import ParametresEtablissement
from finance.models import MODES_PAIEMENT


def fcfa(valeur):
    return f'{valeur:,.0f}'.replace(',', ' ')


def _commun(operation, par):
    return {'operation': operation, 'parametres': ParametresEtablissement.get(), 'emis_le': timezone.now(),
            'par': par.get_username() if par else None}


def contexte_paiement_etudiant(p):
    from finance.models import FraisScolarite
    dossier = FraisScolarite.objects.select_related('inscription__etudiant__personne', 'inscription__classe').get(
        pk=p.dossier_id)
    i = dossier.inscription
    return {
        **_commun(p.operation, p.par), 'titre': 'Reçu de paiement — frais de scolarité', 'montant': fcfa(p.montant),
        'annule': p.annule, 'motif_annulation': p.motif_annulation, 'reste': dossier.reste,
        'lignes': [('Étudiant', i.etudiant.personne.nom_complet), ('Matricule', i.etudiant.matricule),
                   ('Classe', i.classe.libelle), ('Mode de paiement', dict(MODES_PAIEMENT)[p.mode]),
                   ('Référence', p.reference or '—'), ('Total dû pour l’année', f'{fcfa(dossier.montant_du)} FCFA'),
                   ('Total payé', f'{fcfa(dossier.montant_paye)} FCFA'), ('Reste à payer', f'{fcfa(dossier.reste)} FCFA')],
    }


def contexte_paiement_paie(p):
    from finance.paie import libelle_paie
    from finance.models import Paie
    paie = Paie.objects.select_related('personne', 'vacation__affectation__ec', 'vacation__affectation__classe').get(
        pk=p.paie_id)
    return {
        **_commun(p.operation, p.par), 'titre': 'Reçu de paiement — paie', 'montant': fcfa(p.montant),
        'annule': p.annule, 'motif_annulation': p.motif_annulation,
        'lignes': [('Objet', libelle_paie(paie)), ('Mode de paiement', dict(MODES_PAIEMENT)[p.mode]),
                   ('Référence', p.reference or '—'), ('Montant dû', f'{fcfa(paie.montant_du)} FCFA'),
                   ('Total payé', f'{fcfa(paie.montant_paye)} FCFA'), ('Reste à payer', f'{fcfa(paie.reste)} FCFA')],
    }


def contexte_operation(op):
    from finance.models import Operation
    annulee = Operation.objects.filter(annule=op).first()
    return {
        **_commun(op, op.par), 'titre': 'Reçu — recette' if op.montant > 0 else 'Reçu — dépense',
        'montant': fcfa(abs(op.montant)), 'annule': annulee is not None,
        'motif_annulation': annulee.libelle if annulee else '',
        'lignes': [('Libellé', op.libelle), ('Catégorie', op.get_categorie_display())],
    }


def html_recu(gabarit, contexte):
    return render_to_string(gabarit, {'logo': logo_data_uri(), **contexte})


def recu_paiement_etudiant(p):
    return rendre_pdf('finance/recu_etudiant.html', contexte_paiement_etudiant(p))


def recu_paiement_paie(p):
    return rendre_pdf('finance/recu_paie.html', contexte_paiement_paie(p))


def recu_operation(op):
    return rendre_pdf('finance/recu_operation.html', contexte_operation(op))
