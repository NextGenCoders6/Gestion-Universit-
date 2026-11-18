"""API du secrétariat : étudiants, inscriptions, statuts."""
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import Http404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.filtres import entier
from core.audit import journaliser
from core.models import Classe, ElementConstitutif, Etudiant
from scolarite.models import Inscription, Note
from scolarite.perimetre import q_classe_de_faculte, restreindre_par_faculte
from scolarite.permissions import Secretariat
from scolarite.serializers import (
    EtudiantCreationSerializer, EtudiantFicheSerializer, EtudiantListeSerializer, InscriptionSerializer,
    StatutSerializer,
)

STATUT_INSCRIPTION = {'abandonne': 'abandonnee', 'diplome': 'terminee'}


def inscriptions_visibles(etudiant, user):
    """Inscriptions de l'étudiant dans le périmètre de l'utilisateur (la plus récente d'abord)."""
    qs = etudiant.inscriptions.select_related('classe__parcours', 'classe__portail', 'classe__filiere', 'annee',
                                              'etudiant__personne')
    return restreindre_par_faculte(qs, user, prefixe='classe__').order_by('-annee__date_debut')


def etudiants_du_perimetre(user):
    qs = Etudiant.objects.select_related('personne', 'annee_entree')
    return restreindre_par_faculte(qs, user, prefixe='inscriptions__classe__')


class EtudiantViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                      viewsets.GenericViewSet):
    permission_classes = [Secretariat]

    def get_serializer_class(self):
        if self.action == 'create':
            return EtudiantCreationSerializer
        if self.action == 'retrieve':
            return EtudiantFicheSerializer
        return EtudiantListeSerializer

    def get_queryset(self):
        qs = etudiants_du_perimetre(self.request.user)
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(matricule__icontains=q) | Q(personne__nom__icontains=q) | Q(personne__prenom__icontains=q))
        classe = entier(self.request, 'classe')
        if classe is not None:
            qs = qs.filter(inscriptions__classe_id=classe)
        annee = entier(self.request, 'annee')
        if annee is not None:
            qs = qs.filter(inscriptions__annee_id=annee)
        faculte = entier(self.request, 'faculte')
        if faculte is not None:
            qs = qs.filter(q_classe_de_faculte(faculte, 'inscriptions__classe__'))
        if params.get('statut'):
            qs = qs.filter(statut=params['statut'])
        # Seules les inscriptions du périmètre sont montrées (un étudiant transféré garde l'autre faculté hors de vue).
        inscriptions = restreindre_par_faculte(
            Inscription.objects.select_related('classe', 'annee', 'classe__parcours', 'etudiant__personne'),
            self.request.user, prefixe='classe__').order_by('-annee__date_debut')
        return qs.distinct().prefetch_related(Prefetch('inscriptions', queryset=inscriptions))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        etudiant = serializer.save()
        journaliser(request, 'scolarite', 'creation_etudiant', f'{etudiant.matricule} — {etudiant.personne}')
        etudiant = self.get_queryset().get(pk=etudiant.pk)
        return Response(EtudiantFicheSerializer(etudiant, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def statut(self, request, pk=None):
        etudiant = self.get_object()
        # Le statut suit l'inscription la plus récente : elle doit être dans le périmètre.
        derniere = Inscription.objects.filter(etudiant=etudiant).order_by('-annee__date_debut').first()
        if derniere is not None and not inscriptions_visibles(etudiant, request.user).filter(pk=derniere.pk).exists():
            raise Http404
        serializer = StatutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        etudiant.statut = serializer.validated_data['statut']
        etudiant.save()
        statut_inscription = STATUT_INSCRIPTION.get(etudiant.statut)
        if statut_inscription:
            for inscription in etudiant.inscriptions.filter(statut='active'):
                inscription.statut = statut_inscription
                inscription.save()
        journaliser(request, 'scolarite', 'statut_etudiant', f'{etudiant.matricule} → {etudiant.statut}')
        return Response(EtudiantFicheSerializer(self.get_object(), context={'request': request}).data)


class InscriptionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                         mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [Secretariat]
    serializer_class = InscriptionSerializer

    def get_queryset(self):
        qs = Inscription.objects.select_related('etudiant__personne', 'classe__parcours', 'annee')
        qs = restreindre_par_faculte(qs, self.request.user, prefixe='classe__')
        for nom in ('classe', 'annee', 'etudiant'):
            valeur = entier(self.request, nom)
            if valeur is not None:
                qs = qs.filter(**{f'{nom}_id': valeur})
        if self.request.query_params.get('statut'):
            qs = qs.filter(statut=self.request.query_params['statut'])
        return qs

    def perform_create(self, serializer):
        inscription = serializer.save()
        journaliser(self.request, 'scolarite', 'inscription', f'{inscription}')

    @transaction.atomic
    def perform_update(self, serializer):
        inscription = serializer.instance
        classe = serializer.validated_data.get('classe', inscription.classe)
        if classe.pk == inscription.classe_id:
            serializer.save()
            return
        if classe.annee_id != inscription.annee_id:
            raise ValidationError({'classe': "Le changement de classe se fait dans la même année."})
        if inscription.notes.filter(Q(note_devoir__isnull=False) | Q(note_session__isnull=False)
                                    | Q(note_sr__isnull=False) | Q(est_absent=True)).exists() \
                or inscription.resultats.exists():
            raise ValidationError({'classe': 'Des notes sont déjà saisies : la classe ne peut plus changer.'})
        ancienne = inscription.classe
        inscription = serializer.save()
        inscription.notes.all().delete()
        Note.objects.bulk_create([Note(inscription=inscription, ec=ec) for ec in classe.ecs_au_programme()])
        from scolarite.inscriptions import APRES_CHANGEMENT_CLASSE
        for rappel in list(APRES_CHANGEMENT_CLASSE):
            rappel(inscription)
        journaliser(self.request, 'scolarite', 'changement_classe', f'{inscription.etudiant.matricule} : '
                                                                     f'{ancienne} → {classe}')


class ClassesView(APIView):
    """Classes du périmètre avec leur programme (EC par semestre), pour les écrans de la Scolarité."""

    permission_classes = [Secretariat]

    def get(self, request):
        classes = restreindre_par_faculte(
            Classe.objects.select_related('annee', 'parcours', 'portail', 'filiere'), request.user)
        annee = entier(request, 'annee')
        if annee is not None:
            classes = classes.filter(annee_id=annee)
        classes = list(classes.order_by('-annee__date_debut', 'parcours__type_parcours', 'parcours__niveau', 'libelle'))
        programme = {}
        for ec in ElementConstitutif.objects.select_related('ue').order_by('ue__semestre', 'ue__code', 'code'):
            ue = ec.ue
            programme.setdefault(('p', ue.portail_id) if ue.portail_id else ('f', ue.filiere_id), []).append(ec)
        resultat = []
        for c in classes:
            cle = ('p', c.portail_id) if c.portail_id else ('f', c.filiere_id)
            resultat.append({
                'id': c.pk, 'libelle': c.libelle, 'annee': c.annee_id, 'annee_libelle': c.annee.libelle,
                'niveau': c.parcours.code, 'semestres': list(c.semestres), 'portail': c.portail_id,
                'filiere': c.filiere_id, 'archivee': c.annee.statut == 'archivee',
                'ecs': [{'id': ec.pk, 'code': ec.code, 'libelle': ec.libelle, 'semestre': ec.ue.semestre,
                         'credits': ec.credits} for ec in programme.get(cle, []) if ec.ue.semestre in c.semestres],
            })
        return Response(resultat)
