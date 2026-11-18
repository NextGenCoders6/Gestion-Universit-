"""API du module Emploi du temps (/api/edt/…), portée de EDT_app/views.py."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.filtres import entier
from core.droits import a_droit
from core.models import AnneeAcademique, Classe, Enseignant
from edt import quotas
from edt.droits import enseignant_de
from edt.models import AffectationEC, DocumentPedagogique, ReferentClasse, Seance
from edt.perimetre import classes_autorisees, filtrer_par_classes, peut_gerer_classe, restreindre_enseignants
from edt.validation import q_jour_effectif, valider_annee_non_archivee
from edt.permissions import LectureEdt
from edt.serializers import (
    AffectationSerializer, DocumentSerializer, EnseignantSerializer, ReferentSerializer, ReportSerializer, SeanceSerializer,
)

RELATIONS_SEANCE = ('ec', 'classe__annee', 'classe__parcours', 'classe__portail', 'classe__filiere',
                    'enseignant__personne')


def _date(request, nom):
    valeur = request.query_params.get(nom)
    if not valeur:
        return None
    from datetime import date
    try:
        return date.fromisoformat(valeur)
    except ValueError:
        raise ValidationError({nom: 'Date invalide (AAAA-MM-JJ attendu).'})


def _verrouiller(enseignants=(), classes=()):
    """Verrouille les séances concernées avant de rejouer les contrôles (comme l'EDT)."""
    q = Q(pk__in=[])
    if enseignants:
        q |= Q(enseignant__in=list(enseignants))
    if classes:
        q |= Q(classe__in=list(classes))
    list(Seance.objects.select_for_update().filter(q).values_list('pk', flat=True))


CHAMPS_CRENEAU = ('date_seance', 'heure_debut', 'heure_fin')


def jumelles_de(seance):
    """Séances mutualisées avec celle-ci (dans les deux sens)."""
    return list(Seance.objects.filter(Q(pk=seance.seance_liee_id) | Q(seance_liee=seance)).exclude(pk=seance.pk))


def enregistrer_paire(seance, jumelles, changements):
    """Applique un même changement de créneau (ou report) à une séance et à ses jumelles, tout ou rien."""
    for j in jumelles:
        for champ, valeur in changements.items():
            setattr(j, champ, valeur)
    groupe = [seance, *jumelles]
    with transaction.atomic():
        for s in groupe:
            s._jumelles_en_cours = [x for x in groupe if x is not s]
            s.save()


class ClasseGereeMixin:
    """Création et changement de classe réservés aux classes du périmètre de gestion."""

    def _exiger_classe_geree(self, classe):
        if not peut_gerer_classe(self.request.user, classe):
            raise PermissionDenied("Cette classe n'est pas dans votre périmètre.")

    def perform_create(self, serializer):
        self._exiger_classe_geree(serializer.validated_data['classe'])
        serializer.save()

    def perform_update(self, serializer):
        if 'classe' in serializer.validated_data:
            self._exiger_classe_geree(serializer.validated_data['classe'])
        serializer.save()


class SeanceViewSet(ClasseGereeMixin, viewsets.ModelViewSet):
    serializer_class = SeanceSerializer
    permission_classes = [LectureEdt]

    def get_queryset(self):
        qs = Seance.objects.select_related(*RELATIONS_SEANCE)
        qs = filtrer_par_classes(qs, classes_autorisees(self.request.user))
        p = self.request
        for nom, champ in (('classe', 'classe_id'), ('enseignant', 'enseignant_id'), ('ec', 'ec_id'),
                           ('annee', 'classe__annee_id')):
            valeur = entier(p, nom)
            if valeur is not None:
                qs = qs.filter(**{champ: valeur})
        statut = p.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        debut, fin = _date(p, 'date_debut'), _date(p, 'date_fin')
        if debut or fin:
            qs = qs.filter(q_jour_effectif(debut, fin))
        return qs

    def _exiger_jumelle_geree(self, serializer):
        liee = serializer.validated_data.get('seance_liee')
        if liee is not None and not peut_gerer_classe(self.request.user, liee.classe):
            raise PermissionDenied("La séance liée n'est pas dans votre périmètre.")

    def perform_create(self, serializer):
        self._exiger_jumelle_geree(serializer)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._exiger_jumelle_geree(serializer)
        if 'classe' in serializer.validated_data:
            self._exiger_classe_geree(serializer.validated_data['classe'])
        seance = serializer.instance
        creneau = {c: serializer.validated_data[c] for c in CHAMPS_CRENEAU if c in serializer.validated_data}
        jumelles = jumelles_de(seance)
        if creneau and jumelles:
            for champ, valeur in serializer.validated_data.items():
                setattr(seance, champ, valeur)
            enregistrer_paire(seance, jumelles, creneau)
        else:
            serializer.save()

    def perform_destroy(self, seance):
        valider_annee_non_archivee(seance.classe.annee)
        seance.delete()

    @action(detail=True, methods=['get'])
    def seances_liees(self, request, pk=None):
        seance = self.get_object()
        visibles = self.get_queryset()  # même périmètre que la liste : rien hors périmètre
        liees = list(visibles.filter(Q(pk=seance.seance_liee_id) | Q(seance_liee=seance)).exclude(pk=seance.pk))
        return Response({'count': len(liees), 'results': SeanceSerializer(liees, many=True).data})

    @action(detail=True, methods=['post'])
    def publier(self, request, pk=None):
        seance = self.get_object()
        if seance.statut != 'brouillon':
            raise ValidationError('Seules les séances en brouillon peuvent être publiées.')
        with transaction.atomic():
            _verrouiller([seance.enseignant], [seance.classe])
            seance.statut = 'Confirmée'
            seance.save()
        return Response(SeanceSerializer(seance).data)

    @action(detail=True, methods=['post'])
    def depublier(self, request, pk=None):
        seance = self.get_object()
        if seance.statut != 'Confirmée':
            raise ValidationError('Seules les séances confirmées peuvent être dépubliées.')
        seance.statut = 'brouillon'
        seance.save()
        return Response(SeanceSerializer(seance).data)

    @action(detail=False, methods=['post'])
    def publier_masse(self, request):
        ids = request.data.get('seance_ids') if isinstance(request.data, dict) else None
        if not isinstance(ids, list) or not ids:
            raise ValidationError({'seance_ids': 'Liste de séances attendue.'})
        try:
            ids = {int(i) for i in ids}
        except (TypeError, ValueError):
            raise ValidationError({'seance_ids': 'Identifiants invalides.'})
        seances = list(self.get_queryset().filter(pk__in=ids, statut='brouillon'))
        if len(seances) != len(ids):
            raise ValidationError('Certaines séances sont introuvables ou ne sont pas en brouillon.')
        for s in seances:
            if not peut_gerer_classe(request.user, s.classe):
                raise PermissionDenied("Une des séances n'est pas dans votre périmètre.")
        erreurs = []
        try:
            with transaction.atomic():
                _verrouiller([s.enseignant for s in seances], [s.classe for s in seances])
                for s in sorted(seances, key=lambda x: (x.date_seance, x.heure_debut)):
                    s.statut = 'Confirmée'
                    try:
                        s.save()
                    except DjangoValidationError as e:
                        erreurs.append(f'Le {s.date_seance:%d/%m/%Y} ({s.ec.code}, {s.classe.libelle}) : '
                                       + ' '.join(e.messages))
                if erreurs:
                    raise DjangoValidationError(erreurs)
        except DjangoValidationError:
            return Response({'detail': "Impossible de publier l'emploi du temps en raison de conflits.",
                             'erreurs': erreurs}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': f'{len(seances)} séance(s) publiée(s).'})

    @action(detail=True, methods=['patch'])
    def reporter(self, request, pk=None):
        seance = self.get_object()
        if not peut_gerer_classe(request.user, seance.classe):
            raise PermissionDenied("Cette classe n'est pas dans votre périmètre.")
        if seance.statut not in ('Confirmée', 'Reportée'):
            raise ValidationError('Seules les séances publiées peuvent être reportées.')
        donnees = ReportSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        report = {**donnees.validated_data, 'statut': 'Reportée'}
        with transaction.atomic():
            _verrouiller([seance.enseignant], [seance.classe])
            for champ, valeur in report.items():
                setattr(seance, champ, valeur)
            enregistrer_paire(seance, jumelles_de(seance), report)
        return Response(SeanceSerializer(seance).data)

    @action(detail=False, methods=['get'])
    def conflits(self, request):
        """Séances publiées qui se chevauchent (même classe, ou même enseignant hors mutualisation)."""
        annee = entier(request, 'annee') or getattr(AnneeAcademique.courante(), 'pk', None)
        qs = self.get_queryset().filter(classe__annee_id=annee, statut__in=['Confirmée', 'Reportée'])
        par_jour = {}
        for s in qs:
            jour, debut, fin = s.creneau_effectif()
            par_jour.setdefault(jour, []).append((s, debut, fin))
        en_conflit = set()
        for liste in par_jour.values():
            for i, (a, d1, f1) in enumerate(liste):
                for (b, d2, f2) in liste[i + 1:]:
                    if not (d2 < f1 and f2 > d1):
                        continue
                    mutualisees = a.seance_liee_id == b.pk or b.seance_liee_id == a.pk
                    if a.classe_id == b.classe_id or (a.enseignant_id == b.enseignant_id and not mutualisees):
                        en_conflit.update((a.pk, b.pk))
        seances = Seance.objects.filter(pk__in=en_conflit).select_related(*RELATIONS_SEANCE)
        return Response({'count': len(en_conflit), 'results': SeanceSerializer(seances, many=True).data})


class AffectationViewSet(ClasseGereeMixin, viewsets.ModelViewSet):
    serializer_class = AffectationSerializer
    permission_classes = [LectureEdt]

    def get_queryset(self):
        qs = AffectationEC.objects.select_related('ec', 'classe__annee', 'classe__parcours', 'classe__portail',
                                                   'classe__filiere', 'enseignant__personne')
        qs = filtrer_par_classes(qs, classes_autorisees(self.request.user))
        for nom, champ in (('ec', 'ec_id'), ('classe', 'classe_id'), ('enseignant', 'enseignant_id'),
                           ('annee', 'classe__annee_id')):
            valeur = entier(self.request, nom)
            if valeur is not None:
                qs = qs.filter(**{champ: valeur})
        return qs

    def perform_destroy(self, affectation):
        valider_annee_non_archivee(affectation.classe.annee)
        affectation.delete()

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        lignes = list(page if page is not None else qs)
        contexte = {**self.get_serializer_context(), **contexte_quotas({a.classe_id for a in lignes})}
        data = AffectationSerializer(lignes, many=True, context=contexte).data
        return self.get_paginated_response(data) if page is not None else Response(data)


def contexte_quotas(classes_ids):
    """Totaux d'heures et volumes affectés des classes données, pour AffectationSerializer."""
    from collections import defaultdict
    volumes = defaultdict(float)
    for ec_id, classe_id, heures in AffectationEC.objects.filter(classe_id__in=classes_ids).values_list(
            'ec_id', 'classe_id', 'heures_prevues'):
        volumes[(ec_id, classe_id)] += heures
    return {'totaux': quotas.Totaux(classes_ids), 'volumes': volumes}


def ecs_de_classe(classe):
    """EC au programme d'une classe (voir Classe.ecs_au_programme)."""
    return classe.ecs_au_programme()


class EnseignementsView(APIView):
    """Une ligne par (EC, classe) du périmètre : quotas, avancement, affectations."""

    permission_classes = [LectureEdt]

    def get(self, request):
        annee = entier(request, 'annee') or getattr(AnneeAcademique.courante(), 'pk', None)
        classes = Classe.objects.filter(annee_id=annee).select_related('parcours', 'portail', 'filiere', 'annee')
        classes = filtrer_par_classes(classes, classes_autorisees(request.user), champ='pk')
        classe_id = entier(request, 'classe')
        if classe_id is not None:
            classes = classes.filter(pk=classe_id)
        departement = entier(request, 'departement')
        classes = list(classes.order_by('parcours__type_parcours', 'parcours__niveau', 'libelle'))
        ids = {c.pk for c in classes}
        contexte = contexte_quotas(ids)
        totaux = contexte['totaux']
        affectations = {}
        for a in AffectationEC.objects.filter(classe_id__in=ids).select_related('ec', 'classe', 'enseignant__personne'):
            affectations.setdefault((a.ec_id, a.classe_id), []).append(a)
        lignes = []
        for classe in classes:
            ecs = ecs_de_classe(classe)
            if departement is not None:
                ecs = ecs.filter(departement_id=departement)
            for ec in ecs.order_by('ue__semestre', 'code'):
                liste = affectations.get((ec.pk, classe.pk), [])
                lignes.append({
                    'ec': ec.pk, 'ec_code': ec.code, 'ec_libelle': ec.libelle, 'semestre': ec.ue.semestre,
                    'departement': ec.departement_id, 'departement_libelle': ec.departement.libelle,
                    'classe': classe.pk, 'classe_libelle': classe.libelle,
                    'heures_max': quotas.heures_max(ec),
                    'plafonds': {t: quotas.plafond_type(ec, t) for t in ('CM', 'TD', 'TP')},
                    'heures_consommees': totaux.consommees(ec.pk, classe.pk),
                    'heures_effectuees': totaux.effectuees(ec.pk, classe.pk),
                    'affectations': AffectationSerializer(liste, many=True, context=contexte).data,
                })
        return Response({'count': len(lignes), 'results': lignes})


class ReferentViewSet(viewsets.ModelViewSet):
    serializer_class = ReferentSerializer
    permission_classes = [LectureEdt]
    queryset = ReferentClasse.objects.select_related('enseignant__personne').prefetch_related('classes')

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and not (
                request.user.is_superuser or a_droit(request.user, 'edt', 'responsable')):
            raise PermissionDenied('Seuls les responsables de l’emploi du temps désignent les référents.')


class EnseignantViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = EnseignantSerializer
    permission_classes = [LectureEdt]

    def get_queryset(self):
        qs = Enseignant.objects.select_related('personne', 'departement').order_by('personne__nom')
        qs = restreindre_enseignants(self.request.user, qs)
        dep = entier(self.request, 'departement')
        return qs.filter(departement_id=dep) if dep is not None else qs


# ── Espace enseignant ────────────────────────────────────────────

class EstEnseignant(BasePermission):
    message = 'Réservé aux enseignants.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and enseignant_de(request.user))


class MonPlanningView(APIView):
    permission_classes = [IsAuthenticated, EstEnseignant]

    def get(self, request):
        qs = Seance.objects.filter(enseignant=enseignant_de(request.user), statut__in=['Confirmée', 'Reportée'])
        debut, fin = _date(request, 'date_debut'), _date(request, 'date_fin')
        if debut or fin:
            qs = qs.filter(q_jour_effectif(debut, fin))
        return Response(SeanceSerializer(qs.select_related(*RELATIONS_SEANCE), many=True).data)


class MesEnseignementsView(APIView):
    permission_classes = [IsAuthenticated, EstEnseignant]

    def get(self, request):
        qs = AffectationEC.objects.filter(enseignant=enseignant_de(request.user)).select_related(
            'ec', 'classe__annee', 'enseignant__personne')
        annee = entier(request, 'annee')
        if annee is not None:
            qs = qs.filter(classe__annee_id=annee)
        return Response(AffectationSerializer(qs, many=True).data)


# ── Documents pédagogiques ───────────────────────────────────────

def reponse_telechargement(document):
    import os
    from django.http import FileResponse
    return FileResponse(document.fichier.open('rb'), as_attachment=True,
                        filename=os.path.basename(document.fichier.name))


class DocumentViewSet(ClasseGereeMixin, viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [LectureEdt]

    def get_queryset(self):
        qs = DocumentPedagogique.objects.select_related('ec', 'classe', 'enseignant__personne')
        qs = filtrer_par_classes(qs, classes_autorisees(self.request.user))
        for nom, champ in (('ec', 'ec_id'), ('classe', 'classe_id'), ('enseignant', 'enseignant_id')):
            valeur = entier(self.request, nom)
            if valeur is not None:
                qs = qs.filter(**{champ: valeur})
        return qs

    @action(detail=True, methods=['get'])
    def telecharger(self, request, pk=None):
        return reponse_telechargement(self.get_object())

    def perform_destroy(self, document):
        valider_annee_non_archivee(document.classe.annee)
        document.fichier.delete(save=False)
        document.delete()


class MesDocumentsView(APIView):
    """L'enseignant dépose des documents pour les EC qui lui sont affectés."""

    permission_classes = [IsAuthenticated, EstEnseignant]

    def get(self, request):
        qs = DocumentPedagogique.objects.filter(enseignant=enseignant_de(request.user)).select_related('ec', 'classe')
        return Response(DocumentSerializer(qs, many=True).data)

    def post(self, request):
        ens = enseignant_de(request.user)
        serializer = DocumentSerializer(data=request.data, context={'enseignant_impose': True})
        serializer.is_valid(raise_exception=True)
        ec, classe = serializer.validated_data['ec'], serializer.validated_data['classe']
        if not AffectationEC.objects.filter(ec=ec, classe=classe, enseignant=ens).exists():
            raise PermissionDenied("Vous n'êtes pas affecté à cet EC dans cette classe.")
        serializer.save(enseignant=ens)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MonDocumentTelechargementView(APIView):
    permission_classes = [IsAuthenticated, EstEnseignant]

    def get(self, request, pk):
        from django.shortcuts import get_object_or_404
        doc = get_object_or_404(DocumentPedagogique, pk=pk, enseignant=enseignant_de(request.user))
        return reponse_telechargement(doc)
