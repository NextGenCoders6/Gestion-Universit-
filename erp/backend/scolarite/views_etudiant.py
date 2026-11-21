"""Espace étudiant (notes, planning, enseignants)."""
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import AnneeAcademique
from edt.models import AffectationEC, Seance
from edt.serializers import SeanceSerializer
from edt.validation import q_jour_effectif
from edt.views import RELATIONS_SEANCE, _date
from scolarite.inscriptions import MOTIFS_MASQUAGE_RESULTATS
from scolarite.moteur import ligne_etudiant
from scolarite.serialisation import ligne_json, resultat_json

# ── Espace étudiant ──────────────────────────────────────────────

class EstEtudiant(BasePermission):
    message = 'Réservé aux étudiants.'

    def has_permission(self, request, view):
        personne = getattr(request.user, 'personne', None)
        return personne is not None and hasattr(personne, 'etudiant')


def etudiant_de(user):
    return user.personne.etudiant


def inscription_courante(etudiant):
    """Inscription de l'année en cours, sinon la plus récente non abandonnée."""
    inscriptions = etudiant.inscriptions.exclude(statut='abandonnee').select_related('classe', 'annee')
    courante = AnneeAcademique.courante()
    return (inscriptions.filter(annee=courante).first() if courante else None) or inscriptions.first()


class MesNotesView(APIView):
    """Notes saisies de l'étudiant ; moyenne et décision seulement une fois le semestre délibéré."""

    permission_classes = [IsAuthenticated, EstEtudiant]

    def get(self, request):
        etudiant = etudiant_de(request.user)
        donnees = []
        for inscription in etudiant.inscriptions.exclude(statut='abandonnee').select_related(
                'classe__parcours', 'annee', 'etudiant__personne'):
            motif = next((m for m in (f(inscription) for f in MOTIFS_MASQUAGE_RESULTATS) if m), None)
            resultats = {} if motif else {r.semestre: r for r in inscription.resultats.all()}
            delibere = {r.semestre for r in inscription.resultats.all()}
            semestres = []
            for semestre in inscription.classe.semestres:
                ligne = ligne_json(ligne_etudiant(inscription, semestre))
                resultat = resultats.get(semestre)
                semestres.append({'semestre': semestre, 'deliberee': semestre in delibere,
                                  'resultat': resultat_json(resultat), 'ues': [
                                      {k: v for k, v in ue.items() if k not in ('moyenne_ue', 'validee')}
                                      | ({'moyenne_ue': ue['moyenne_ue'], 'validee': ue['validee']} if resultat else {})
                                      for ue in ligne['ues']]})
            donnees.append({'inscription': inscription.pk, 'annee': inscription.annee.libelle,
                            'classe': inscription.classe.libelle, 'statut': inscription.statut,
                            'resultats_masques': bool(motif), 'message_resultats': motif, 'semestres': semestres})
        return Response({'matricule': etudiant.matricule, 'inscriptions': donnees})


class MonPlanningEtudiantView(APIView):
    permission_classes = [IsAuthenticated, EstEtudiant]

    def get(self, request):
        inscription = inscription_courante(etudiant_de(request.user))
        if inscription is None:
            return Response([])
        qs = Seance.objects.filter(classe_id=inscription.classe_id, statut__in=['Confirmée', 'Reportée'])
        debut, fin = _date(request, 'date_debut'), _date(request, 'date_fin')
        if debut or fin:
            qs = qs.filter(q_jour_effectif(debut, fin))
        return Response(SeanceSerializer(qs.select_related(*RELATIONS_SEANCE), many=True).data)


class MesEnseignantsView(APIView):
    """Trombinoscope : enseignants affectés à la classe de l'étudiant, avec leurs EC."""

    permission_classes = [IsAuthenticated, EstEtudiant]

    def get(self, request):
        inscription = inscription_courante(etudiant_de(request.user))
        if inscription is None:
            return Response([])
        par_enseignant = {}
        for a in (AffectationEC.objects.filter(classe_id=inscription.classe_id)
                  .select_related('enseignant__personne', 'ec')
                  .order_by('enseignant__personne__nom', 'ec__code')):
            ens = a.enseignant
            fiche = par_enseignant.setdefault(ens.pk, {
                'id': ens.pk, 'nom_complet': ens.personne.nom_complet, 'grade': ens.grade,
                'photo': request.build_absolute_uri(ens.personne.photo.url) if ens.personne.photo else None,
                'ecs': [],
            })
            if all(x['code'] != a.ec.code for x in fiche['ecs']):
                fiche['ecs'].append({'id': a.ec.pk, 'code': a.ec.code, 'libelle': a.ec.libelle})
        return Response(list(par_enseignant.values()))
