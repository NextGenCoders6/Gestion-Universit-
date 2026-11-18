"""Documents officiels (PDF) et page publique de vérification."""
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from core.api.filtres import entier
from core.audit import journaliser
from core.documents import reponse_pdf
from scolarite.documents import attestation_pdf, matrice_pdf, releve_pdf
from scolarite.models import DocumentEmis
from scolarite.permissions import DroitScolarite, Faculte
from scolarite.views_faculte import classe_demandee, programme_ou_400
from scolarite.views_secretariat import etudiants_du_perimetre


def _inscription(request, pk):
    etudiant = get_object_or_404(etudiants_du_perimetre(request.user), pk=pk)
    inscriptions = etudiant.inscriptions.select_related('classe__parcours', 'classe__portail', 'classe__filiere',
                                                        'annee', 'etudiant__personne')
    annee = entier(request, 'annee')
    inscription = (inscriptions.filter(annee_id=annee) if annee is not None else inscriptions).first()
    if inscription is None:
        raise ValidationError({'detail': "L'étudiant n'a pas d'inscription pour cette année."})
    return inscription


def _avec_verification(reponse, url):
    """L'adresse encodée dans le QR code, pour qui veut l'archiver sans relire le PDF."""
    reponse['X-Verification-Url'] = url
    return reponse


class AttestationView(APIView):
    permission_classes = [DroitScolarite('secretariat')]

    def get(self, request, pk):
        inscription = _inscription(request, pk)
        if inscription.statut == 'abandonnee':
            raise ValidationError({'detail': "L'étudiant a abandonné : aucune attestation de fréquentation."})
        contenu, url = attestation_pdf(inscription, request.user)
        journaliser(request, 'scolarite', 'attestation', f'{inscription}')
        return _avec_verification(reponse_pdf(contenu, f'attestation-{inscription.etudiant.matricule}.pdf'), url)


class ReleveView(APIView):
    permission_classes = [DroitScolarite('secretariat')]

    def get(self, request, pk):
        inscription = _inscription(request, pk)
        semestre = request.query_params.get('semestre', '')
        programme_ou_400(inscription.classe, semestre)
        resultat = inscription.resultats.filter(semestre=semestre).first()
        if resultat is None:
            raise ValidationError({'detail': f"Le semestre {semestre} n'est pas encore délibéré pour cet étudiant."})
        contenu, url = releve_pdf(inscription, semestre, resultat, request.user)
        journaliser(request, 'scolarite', 'releve', f'{inscription} — {semestre}')
        return _avec_verification(reponse_pdf(contenu, f'releve-{inscription.etudiant.matricule}-{semestre}.pdf'), url)


class MatriceA3View(APIView):
    permission_classes = [Faculte]

    def get(self, request):
        classe = classe_demandee(request)
        semestre = request.query_params.get('semestre', '')
        programme_ou_400(classe, semestre)
        nom = f'pv-{classe.parcours.code}-{(classe.portail or classe.filiere).code}-{semestre}.pdf'
        return reponse_pdf(matrice_pdf(classe, semestre), nom)


@require_GET
def verifier_document(request, jeton):
    """Page publique : confirme l'authenticité sans détailler les notes."""
    document = (DocumentEmis.objects.select_related('inscription__etudiant__personne', 'inscription__classe')
                .filter(jeton=jeton).first())
    return render(request, 'scolarite/verification.html', {'document': document}, status=200 if document else 404)
