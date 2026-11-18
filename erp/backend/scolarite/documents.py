"""Attestation, relevé de notes et matrice A3 (procès-verbal de délibération)."""
from django.conf import settings
from django.utils import timezone
from django.utils.formats import date_format

from core.documents import qr_data_uri, rendre_pdf
from core.models import ParametresEtablissement
from scolarite.models import DocumentEmis
from scolarite.moteur import deliberation, ligne_etudiant, programme

CYCLES = {'Licence': 'Licence', 'Master': 'Master'}


def _date_du_jour():
    return date_format(timezone.localdate(), 'j F Y')


def _commun(inscription):
    personne = inscription.etudiant.personne
    classe = inscription.classe
    parametres = ParametresEtablissement.get()
    return {
        'etudiant': inscription.etudiant, 'personne': personne, 'inscription': inscription, 'classe': classe,
        'faculte': classe.faculte, 'parcours': classe.portail or classe.filiere,
        'cycle': CYCLES.get(classe.parcours.type_parcours, classe.parcours.type_parcours),
        'titre': 'Mademoiselle' if personne.genre == 'F' else 'Monsieur',
        'parametres': parametres,
        'titre_secretaire': 'La Secrétaire Universitaire' if parametres.genre_secretaire == 'F'
        else 'Le Secrétaire Universitaire',
        'date': _date_du_jour(),
    }


def _qr(document):
    url = f'{settings.BASE_URL}/verifier/{document.jeton}'
    return {'document': document, 'url_verification': url, 'qr': qr_data_uri(url)}


def contexte_attestation(inscription, par):
    document = DocumentEmis.objects.create(type='attestation', inscription=inscription, emis_par=par)
    return {**_commun(inscription), **_qr(document)}


def attestation_pdf(inscription, par):
    return rendre_pdf('scolarite/attestation.html', contexte_attestation(inscription, par))


def releve_pdf(inscription, semestre, resultat, par):
    """Relevé officiel d'un semestre délibéré : moyennes d'UE et résultat enregistré."""
    document = DocumentEmis.objects.create(type='releve', inscription=inscription, semestre=semestre,
                                           decision=resultat.decision, emis_par=par)
    ligne = ligne_etudiant(inscription, semestre)
    return rendre_pdf('scolarite/releve.html', {
        **_commun(inscription), **_qr(document), 'semestre': semestre, 'ligne': ligne, 'resultat': resultat,
    })


def matrice_pdf(classe, semestre):
    prog = programme(classe, semestre)
    lignes = deliberation(classe, semestre)
    parametres = ParametresEtablissement.get()
    titre_doyen, nom_doyen = classe.faculte.signataire_pv
    return rendre_pdf('scolarite/matrice_a3.html', {
        'classe': classe, 'faculte': classe.faculte, 'semestre': semestre, 'prog': prog, 'lignes': lignes,
        'parcours': classe.portail or classe.filiere, 'parametres': parametres, 'date': _date_du_jour(),
        'titre_doyen': titre_doyen, 'nom_doyen': nom_doyen,
        'titre_secretaire': 'La Secrétaire Universitaire' if parametres.genre_secretaire == 'F'
        else 'Le Secrétaire Universitaire',
    })
