"""API des ressources humaines : tableau de bord, enseignants, personnel, contrats, vacations."""
from datetime import date

from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.filtres import entier
from core.audit import journaliser
from core.droits import a_droit, faculte_rattachee
from core.models import AnneeAcademique, Departement, Employe, Enseignant
from rh import vacations as service
from rh.contrats import contrats_a_echeance, q_en_cours, terminer
from rh.models import Contrat, HistoriqueVacation
from rh.permissions import LectureRH, LectureVacations
from rh.serializers import ContratSerializer, EmployeRHSerializer, EnseignantRHSerializer


def contrats_en_cours_par_personne(personne_ids=None):
    qs = Contrat.objects.filter(q_en_cours(timezone.localdate()))
    if personne_ids is not None:
        qs = qs.filter(personne_id__in=list(personne_ids))
    return {c.personne_id: c for c in qs}


class FicheViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                   mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [LectureRH]
    action_creation = ''

    def filtrer(self, qs):
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(matricule__icontains=q) | Q(personne__nom__icontains=q) | Q(personne__prenom__icontains=q))
        en_cours = Contrat.objects.filter(q_en_cours(timezone.localdate()), personne_id=OuterRef('pk'))
        if params.get('type') in ('permanent', 'vacataire'):
            qs = qs.filter(Exists(en_cours.filter(type=params['type'])))
        if params.get('actif') in ('true', 'false'):
            qs = qs.filter(Exists(en_cours)) if params['actif'] == 'true' else qs.exclude(Exists(en_cours))
        return qs

    def get_serializer_context(self):
        contexte = super().get_serializer_context()
        if self.action == 'list':
            contexte['contrats_en_cours'] = contrats_en_cours_par_personne()
        return contexte

    def perform_create(self, serializer):
        objet = serializer.save()
        journaliser(self.request, 'rh', self.action_creation, f'{objet}')

    def retrieve(self, request, *args, **kwargs):
        objet = self.get_object()
        donnees = self.get_serializer(objet).data
        donnees['contrats'] = ContratSerializer(objet.personne.contrats.order_by('-date_debut'), many=True,
                                                context={'request': request}).data
        return Response(donnees)


class EnseignantViewSet(FicheViewSet):
    serializer_class = EnseignantRHSerializer
    action_creation = 'creation_enseignant'

    def get_queryset(self):
        qs = Enseignant.objects.select_related('personne', 'departement__faculte')
        departement = entier(self.request, 'departement')
        if departement is not None:
            qs = qs.filter(departement_id=departement)
        return self.filtrer(qs)

    def retrieve(self, request, *args, **kwargs):
        reponse = super().retrieve(request, *args, **kwargs)
        enseignant = self.get_object()
        annee = AnneeAcademique.courante()
        affectations = list(enseignant.affectations.filter(classe__annee=annee).select_related(
            'ec', 'classe', 'enseignant__personne', 'vacation')) if annee else []
        heures = service.Heures(affectations)
        reponse.data['affectations'] = [ligne_vacation(a, service.etat(a, heures)) for a in affectations]
        return reponse


class EmployeViewSet(FicheViewSet):
    serializer_class = EmployeRHSerializer
    action_creation = 'creation_employe'

    def get_queryset(self):
        qs = Employe.objects.select_related('personne', 'faculte_rattachement')
        if self.request.query_params.get('fonction'):
            qs = qs.filter(fonction=self.request.query_params['fonction'])
        return self.filtrer(qs)


class ContratViewSet(viewsets.ModelViewSet):
    permission_classes = [LectureRH]
    serializer_class = ContratSerializer

    def get_queryset(self):
        qs = Contrat.objects.select_related('personne__enseignant', 'personne__employe')
        jour = timezone.localdate()
        personne = entier(self.request, 'personne')
        if personne is not None:
            qs = qs.filter(personne_id=personne)
        etat = self.request.query_params.get('etat')
        if etat == 'en_cours':
            qs = qs.filter(q_en_cours(jour))
        elif etat == 'expire':
            qs = qs.filter(date_fin__lt=jour)
        elif etat == 'a_venir':
            qs = qs.filter(date_debut__gt=jour)
        echeance = entier(self.request, 'echeance')
        if echeance is not None:
            qs = qs.filter(pk__in=contrats_a_echeance(echeance).values('pk'))
        return qs

    def perform_create(self, serializer):
        contrat = serializer.save()
        journaliser(self.request, 'rh', 'contrat', f'Création : {contrat}')

    def perform_update(self, serializer):
        contrat = serializer.save()
        journaliser(self.request, 'rh', 'contrat', f'Modification : {contrat}')

    @action(detail=True, methods=['post'])
    def terminer(self, request, pk=None):
        contrat = self.get_object()
        try:
            fin = date.fromisoformat(str(request.data.get('date_fin', '')))
        except ValueError:
            raise ValidationError({'date_fin': 'Date invalide (AAAA-MM-JJ attendu).'})
        terminer(contrat, fin)
        journaliser(request, 'rh', 'fin_contrat', f'{contrat}')
        return Response(self.get_serializer(contrat).data)


# ── Vacations ────────────────────────────────────────────────────

def ligne_vacation(a, e):
    v = e['vacation']
    return {
        'affectation': a.pk, 'ec': a.ec_id, 'ec_code': a.ec.code, 'ec_libelle': a.ec.libelle, 'classe': a.classe_id,
        'classe_libelle': a.classe.libelle, 'enseignant': a.enseignant_id,
        'enseignant_nom': a.enseignant.personne.nom_complet, 'type_seance': a.type_seance,
        'heures_prevues': e['heures_prevues'], 'heures_effectuees': e['heures_effectuees'],
        'heures_jumelles': e['heures_jumelles'], 'heures_dues': e['heures_dues'], 'terminee': e['terminee'],
        'confirmable': e['confirmable'], 'motif_blocage': e['motif_blocage'],
        'taux_horaire': float(e['contrat'].taux_horaire) if e['contrat'] else None,
        'vacation': None if v is None else {
            'heures_retenues': float(v.heures_retenues), 'taux_horaire': float(v.taux_horaire),
            'montant': float(v.montant), 'motif': v.motif, 'confirmee_le': v.confirmee_le,
        },
    }


def affectations_de_vacataires(request):
    """Affectations de l'année dont l'enseignant est vacataire (contrat sur l'année) ou déjà confirmées."""
    from edt.models import AffectationEC
    annee = AnneeAcademique.objects.filter(pk=entier(request, 'annee')).first() if entier(request, 'annee') \
        else AnneeAcademique.courante()
    if annee is None:
        return AffectationEC.objects.none()
    vacataires = Contrat.objects.filter(type='vacataire', date_debut__lte=annee.date_fin).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=annee.date_debut)).values('personne_id')
    qs = (AffectationEC.objects.filter(classe__annee=annee)
          .filter(Q(enseignant_id__in=vacataires) | Q(vacation__isnull=False))
          .select_related('ec__departement__faculte', 'classe', 'enseignant__personne', 'vacation'))
    # La faculté ne voit que les EC de sa faculté (rattachement) ; la RH voit tout.
    faculte = None if a_droit(request.user, 'rh') else faculte_rattachee(request.user)
    if faculte is not None:
        qs = qs.filter(ec__departement__faculte=faculte)
    choix = entier(request, 'faculte')
    if choix is not None:
        qs = qs.filter(ec__departement__faculte_id=choix)
    return qs.order_by('enseignant__personne__nom', 'ec__code', 'classe__libelle')


def lignes_vacations(request, affectations):
    affectations = list(affectations)
    heures = service.Heures(affectations)
    contrats = service.contrats_vacataires_en_cours({a.enseignant_id for a in affectations})
    lignes = [ligne_vacation(a, service.etat(a, heures, contrats=contrats)) for a in affectations]
    etat = request.query_params.get('etat')
    if etat == 'a_confirmer':
        lignes = [l for l in lignes if l['vacation'] is None and l['terminee']]
    elif etat == 'en_cours':
        lignes = [l for l in lignes if l['vacation'] is None and not l['terminee']]
    elif etat == 'confirmee':
        lignes = [l for l in lignes if l['vacation'] is not None]
    return lignes


class VacationsView(APIView):
    permission_classes = [LectureVacations]

    def get(self, request):
        return Response(lignes_vacations(request, affectations_de_vacataires(request)))


class HistoriqueVacationsView(APIView):
    permission_classes = [LectureVacations]

    def get(self, request):
        qs = HistoriqueVacation.objects.select_related('affectation__ec__departement__faculte', 'affectation__classe',
                                                       'affectation__enseignant__personne', 'par')
        faculte = None if a_droit(request.user, 'rh') else faculte_rattachee(request.user)
        if faculte is not None:
            qs = qs.filter(affectation__ec__departement__faculte=faculte)
        affectation = entier(request, 'affectation')
        if affectation is not None:
            qs = qs.filter(affectation_id=affectation)
        return Response([{
            'id': h.pk, 'affectation': h.affectation_id, 'action': h.action, 'action_libelle': h.get_action_display(),
            'ec_code': h.affectation.ec.code, 'classe_libelle': h.affectation.classe.libelle,
            'enseignant_nom': h.affectation.enseignant.personne.nom_complet,
            'heures_retenues': float(h.heures_retenues), 'montant': float(h.montant), 'motif': h.motif,
            'par': h.par.get_username() if h.par else None, 'le': h.le,
        } for h in qs[:500]])


# ── Tableau de bord ──────────────────────────────────────────────

class TableauDeBordView(APIView):
    permission_classes = [LectureRH]

    def get(self, request):
        jour = timezone.localdate()
        en_cours = Contrat.objects.filter(q_en_cours(jour))
        par_personne = {c.personne_id: c for c in en_cours}
        enseignants = [p for p in Enseignant.objects.values_list('pk', flat=True) if p in par_personne]
        employes_actifs = Employe.objects.filter(pk__in=list(par_personne))
        libelles = dict(Employe.FONCTION_CHOICES)
        par_fonction = [{'fonction': x['fonction'], 'libelle': libelles.get(x['fonction'], x['fonction']), 'n': x['n']}
                        for x in employes_actifs.values('fonction').annotate(n=Count('pk')).order_by('-n', 'fonction')]
        avenir = Contrat.objects.filter(date_debut__gt=jour).values('personne_id')
        sans_contrat = (Contrat.objects.exclude(personne_id__in=list(par_personne)).exclude(personne_id__in=avenir)
                        .values('personne_id').distinct().count())
        a_confirmer = lignes_vacations(_Requete(request, 'a_confirmer'), affectations_de_vacataires(request))
        return Response({
            'enseignants_actifs': len(enseignants),
            'enseignants_permanents': sum(1 for p in enseignants if par_personne[p].type == 'permanent'),
            'enseignants_vacataires': sum(1 for p in enseignants if par_personne[p].type == 'vacataire'),
            'chefs_departement': Departement.objects.filter(chef__isnull=False).count(),
            'personnel_actif': employes_actifs.count(),
            'personnel_par_fonction': par_fonction,
            'contrats_a_echeance': ContratSerializer(contrats_a_echeance(30), many=True, context={'request': request}).data,
            'personnes_sans_contrat_en_cours': sans_contrat,
            'vacations_a_confirmer': len(a_confirmer),
        })


class _Requete:
    """Vue minimale d'une requête avec un filtre d'état imposé (réutilise lignes_vacations)."""

    def __init__(self, request, etat):
        self.user = request.user
        self.query_params = {**request.query_params.dict(), 'etat': etat}
