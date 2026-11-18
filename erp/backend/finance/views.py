"""API de la Finance : tableau de bord, frais, paie, journal, tarifs ; situation des frais de l'étudiant."""
from datetime import date
from decimal import Decimal

from django.db.models import Exists, F, OuterRef, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.filtres import entier
from core.audit import journaliser
from core.documents import reponse_pdf
from core.models import AnneeAcademique
from finance import frais as service_frais
from finance import paie as service_paie
from finance import paiements, recus
from finance.models import FraisScolarite, Operation, Paie, PaiementEtudiant, PaiementPaie, Tarif
from finance.permissions import Encaissement, LectureFinance, ResponsableFinance, Tarifs
from finance.serialisation import dossier_json, f, operation_json, paie_json, paiement_json


def annee_demandee(request):
    pk = entier(request, 'annee')
    return AnneeAcademique.objects.filter(pk=pk).first() if pk is not None else AnneeAcademique.courante()


def _date(valeur, champ='date'):
    if valeur in (None, ''):
        return None
    try:
        return date.fromisoformat(str(valeur))
    except ValueError:
        raise ValidationError({champ: 'Date invalide (AAAA-MM-JJ attendu).'})


# ── Frais de scolarité ───────────────────────────────────────────

class FraisViewSet(viewsets.ViewSet):
    permission_classes = [LectureFinance]

    def queryset(self, request):
        qs = (FraisScolarite.objects
              .select_related('inscription__etudiant__personne', 'inscription__classe', 'inscription__annee')
              .prefetch_related('echeances'))
        annee = annee_demandee(request)
        if annee is not None:
            qs = qs.filter(inscription__annee=annee)
        classe = entier(request, 'classe')
        if classe is not None:
            qs = qs.filter(inscription__classe_id=classe)
        statut = request.query_params.get('statut')
        if statut == 'non_paye':
            qs = qs.filter(montant_paye__lte=0)
        elif statut == 'paye':
            qs = qs.filter(montant_paye__gt=0, montant_paye__gte=F('montant_du'))
        elif statut == 'partiel':
            qs = qs.filter(montant_paye__gt=0, montant_paye__lt=F('montant_du'))
        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(inscription__etudiant__matricule__icontains=q)
                           | Q(inscription__etudiant__personne__nom__icontains=q)
                           | Q(inscription__etudiant__personne__prenom__icontains=q))
        return qs.order_by('inscription__etudiant__personne__nom', 'inscription__etudiant__personne__prenom')

    def list(self, request):
        from core.pagination import PaginationStandard
        lignes = [dossier_json(d) for d in self.queryset(request)]
        if request.query_params.get('retard') == 'true':
            lignes = [l for l in lignes if l['en_retard']]
        pagination = PaginationStandard()
        page = pagination.paginate_queryset(lignes, request, view=self)
        return pagination.get_paginated_response(page)

    def objet(self, pk):
        return get_object_or_404(FraisScolarite.objects.select_related(
            'inscription__etudiant__personne', 'inscription__classe', 'inscription__annee'), pk=pk)

    def retrieve(self, request, pk=None):
        return Response(dossier_json(self.objet(pk), detail=True))

    @action(detail=True, methods=['post'], permission_classes=[Encaissement])
    def paiements(self, request, pk=None):
        dossier = self.objet(pk)
        p = paiements.encaisser(dossier, request.data.get('montant'), request.data.get('mode'),
                                date=_date(request.data.get('date')), reference=request.data.get('reference', ''),
                                par=request.user)
        journaliser(request, 'finance', 'paiement_frais', f'{p.operation.numero} — {p.operation.libelle} : {p.montant}')
        return Response({'paiement': paiement_json(p), 'dossier': dossier_json(self.objet(pk), detail=True)},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[ResponsableFinance])
    def ajuster(self, request, pk=None):
        dossier = self.objet(pk)
        ancien = dossier.montant_du
        from finance.journal import montant_valide
        service_frais.ajuster(dossier, montant_valide(request.data.get('montant'), positif=False), par=request.user)
        journaliser(request, 'finance', 'ajustement_frais', f'{dossier.inscription} : {ancien} → {request.data.get("montant")}')
        return Response(dossier_json(self.objet(pk), detail=True))

    @action(detail=True, methods=['put'], permission_classes=[ResponsableFinance])
    def echeancier(self, request, pk=None):
        dossier = self.objet(pk)
        lignes = request.data.get('echeances')
        if not isinstance(lignes, list) or not lignes:
            raise ValidationError({'echeances': 'Indiquez les mensualités.'})
        from finance.journal import montant_valide
        try:
            parsees = [(str(l['mois']), _date(l['date_limite'], 'date_limite'), montant_valide(l['montant']))
                       for l in lignes]
        except (KeyError, TypeError, AttributeError):
            raise ValidationError({'echeances': 'Chaque mensualité a un mois, une date limite et un montant.'})
        service_frais.adapter_echeancier(dossier, parsees, par=request.user)
        journaliser(request, 'finance', 'echeancier_adapte', f'{dossier.inscription} : {len(parsees)} mensualité(s)')
        return Response(dossier_json(self.objet(pk), detail=True))


class AnnulerPaiementView(APIView):
    permission_classes = [ResponsableFinance]

    def post(self, request, pk):
        p = get_object_or_404(PaiementEtudiant, pk=pk)
        contre = paiements.annuler_paiement(p, request.data.get('motif', ''), par=request.user)
        journaliser(request, 'finance', 'annulation_paiement', f'{contre.numero} — {contre.libelle}')
        return Response(operation_json(contre))


class RecuPaiementView(APIView):
    permission_classes = [Encaissement]

    def get(self, request, pk):
        p = get_object_or_404(PaiementEtudiant.objects.select_related('operation'), pk=pk)
        return reponse_pdf(recus.recu_paiement_etudiant(p), f'recu-{p.operation.numero}.pdf')


# ── Paie ─────────────────────────────────────────────────────────

class PaieViewSet(viewsets.ViewSet):
    permission_classes = [LectureFinance]

    def queryset(self, request):
        from core.models import Employe, Enseignant
        qs = Paie.objects.select_related('personne', 'vacation__affectation__ec', 'vacation__affectation__classe')
        params = request.query_params
        if params.get('origine') in ('salaire', 'vacation'):
            qs = qs.filter(origine=params['origine'])
        if params.get('mois'):
            filtre = Q(mois=params['mois'])
            if params.get('avec_vacations') == 'true':
                filtre |= Q(origine='vacation')
            qs = qs.filter(filtre)
        if params.get('role') == 'enseignant':
            qs = qs.filter(Exists(Enseignant.objects.filter(pk=OuterRef('personne_id'))))
        elif params.get('role') == 'employe':
            qs = qs.filter(Exists(Employe.objects.filter(pk=OuterRef('personne_id'))))
        statut = params.get('statut')
        if statut == 'en_attente':
            qs = qs.filter(montant_paye__lte=0)
        elif statut == 'paye':
            qs = qs.filter(montant_paye__gt=0, montant_paye__gte=F('montant_du'))
        elif statut == 'partiel':
            qs = qs.filter(montant_paye__gt=0, montant_paye__lt=F('montant_du'))
        q = params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(personne__nom__icontains=q) | Q(personne__prenom__icontains=q))
        return qs.select_related('personne__enseignant', 'personne__employe').order_by(
            '-origine', '-mois', 'personne__nom', 'personne__prenom')   # vacations d'abord

    def list(self, request):
        from core.pagination import PaginationStandard
        pagination = PaginationStandard()
        page = pagination.paginate_queryset(self.queryset(request), request, view=self)
        return pagination.get_paginated_response([paie_json(p) for p in page])

    def retrieve(self, request, pk=None):
        return Response(paie_json(get_object_or_404(Paie, pk=pk), detail=True))

    @action(detail=False, methods=['post'], permission_classes=[ResponsableFinance])
    def generer(self, request):
        mois = str(request.data.get('mois', ''))
        creees, existantes = service_paie.generer_salaires(mois, par=request.user)
        journaliser(request, 'finance', 'generation_paie', f'{mois} : {creees} ligne(s) créée(s)')
        return Response({'mois': mois, 'creees': creees, 'existantes': existantes})

    @action(detail=True, methods=['post'], permission_classes=[ResponsableFinance])
    def paiements(self, request, pk=None):
        ligne = get_object_or_404(Paie, pk=pk)
        p = service_paie.payer(ligne, request.data.get('montant'), request.data.get('mode'),
                               date=_date(request.data.get('date')), reference=request.data.get('reference', ''),
                               par=request.user)
        journaliser(request, 'finance', 'paiement_paie', f'{p.operation.numero} — {p.operation.libelle} : {p.montant}')
        return Response({'paiement': paiement_json(p), 'paie': paie_json(Paie.objects.get(pk=pk), detail=True)},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[ResponsableFinance])
    def ajuster(self, request, pk=None):
        ligne = get_object_or_404(Paie, pk=pk)
        ancien = ligne.montant_du
        service_paie.ajuster(ligne, request.data.get('montant'), par=request.user)
        journaliser(request, 'finance', 'ajustement_paie', f'{ligne} : {ancien} → {request.data.get("montant")}')
        return Response(paie_json(Paie.objects.get(pk=pk), detail=True))


class AnnulerPaiementPaieView(APIView):
    permission_classes = [ResponsableFinance]

    def post(self, request, pk):
        p = get_object_or_404(PaiementPaie, pk=pk)
        contre = service_paie.annuler_paiement_paie(p, request.data.get('motif', ''), par=request.user)
        journaliser(request, 'finance', 'annulation_paiement_paie', f'{contre.numero} — {contre.libelle}')
        return Response(operation_json(contre))


class RecuPaiementPaieView(APIView):
    permission_classes = [Encaissement]

    def get(self, request, pk):
        p = get_object_or_404(PaiementPaie.objects.select_related('operation'), pk=pk)
        return reponse_pdf(recus.recu_paiement_paie(p), f'recu-{p.operation.numero}.pdf')


# ── Journal ──────────────────────────────────────────────────────

class OperationViewSet(viewsets.ViewSet):
    permission_classes = [LectureFinance]

    def list(self, request):
        from core.pagination import PaginationStandard
        qs = Operation.objects.select_related('par', 'annulation')
        debut, fin = _date(request.query_params.get('debut'), 'debut'), _date(request.query_params.get('fin'), 'fin')
        if debut:
            qs = qs.filter(date__gte=debut)
        if fin:
            qs = qs.filter(date__lte=fin)
        if request.query_params.get('categorie'):
            qs = qs.filter(categorie=request.query_params['categorie'])
        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(libelle__icontains=q) | Q(numero__icontains=q))
        pagination = PaginationStandard()
        page = pagination.paginate_queryset(qs, request, view=self)
        return pagination.get_paginated_response([operation_json(o) for o in page])

    def create(self, request):
        op = paiements.operation_manuelle(request.data.get('libelle'), request.data.get('montant'),
                                          _date(request.data.get('date')), par=request.user)
        journaliser(request, 'finance', 'operation_manuelle', f'{op.numero} — {op.libelle} : {op.montant}')
        return Response(operation_json(op), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[ResponsableFinance])
    def annuler(self, request, pk=None):
        op = get_object_or_404(Operation, pk=pk)
        contre = paiements.annuler_operation(op, request.data.get('motif', ''), par=request.user)
        journaliser(request, 'finance', 'annulation_operation', f'{contre.numero} — {contre.libelle}')
        return Response(operation_json(contre))


class RecuOperationView(APIView):
    permission_classes = [Encaissement]

    def get(self, request, pk):
        op = get_object_or_404(Operation, pk=pk)
        return reponse_pdf(recus.recu_operation(op), f'recu-{op.numero}.pdf')


# ── Tableau de bord ──────────────────────────────────────────────

def _mois_precedents(n, jour):
    annee, mois = jour.year, jour.month
    liste = []
    for _ in range(n):
        liste.append((annee, mois))
        annee, mois = (annee - 1, 12) if mois == 1 else (annee, mois - 1)
    return list(reversed(liste))


class TableauDeBordView(APIView):
    permission_classes = [LectureFinance]

    def get(self, request):
        annee = annee_demandee(request)
        dossiers = list(FraisScolarite.objects.filter(inscription__annee=annee).exclude(
            inscription__statut='abandonnee').prefetch_related('echeances')) if annee else []
        attendus = sum((d.montant_du for d in dossiers), Decimal('0'))
        encaisses = sum((min(d.montant_paye, d.montant_du) for d in dossiers), Decimal('0'))
        retards = [service_frais.montant_en_retard(d, echeances=list(d.echeances.all())) for d in dossiers]
        # Un paiement annulé et sa contre-écriture s'effacent : ni recette ni dépense.
        operations = Operation.objects.filter(annule__isnull=True, annulation__isnull=True)
        if annee:
            operations = operations.filter(date__gte=annee.date_debut, date__lte=annee.date_fin)
        recettes = operations.filter(montant__gt=0).aggregate(s=Sum('montant'))['s'] or Decimal('0')
        depenses = -(operations.filter(montant__lt=0).aggregate(s=Sum('montant'))['s'] or Decimal('0'))
        en_attente = Paie.objects.filter(montant_paye__lt=F('montant_du')).aggregate(
            s=Sum(F('montant_du') - F('montant_paye')))['s'] or Decimal('0')
        jour = timezone.localdate()
        mois = _mois_precedents(12, jour)
        debut = date(mois[0][0], mois[0][1], 1)
        par_mois = {}
        for ligne in (Operation.objects.filter(annule__isnull=True, annulation__isnull=True, date__gte=debut, date__lte=jour)
                      .annotate(m=TruncMonth('date'))
                      .values('m').annotate(r=Sum('montant', filter=Q(montant__gt=0)),
                                            d=Sum('montant', filter=Q(montant__lt=0)))):
            par_mois[(ligne['m'].year, ligne['m'].month)] = (ligne['r'] or 0, -(ligne['d'] or 0))
        return Response({
            'annee': annee.pk if annee else None, 'annee_libelle': annee.libelle if annee else None,
            'recettes': f(recettes), 'depenses': f(depenses), 'solde': f(recettes - depenses),
            'frais_attendus': f(attendus), 'frais_encaisses': f(encaisses),
            'taux_recouvrement': round(float(encaisses / attendus * 100), 1) if attendus else 0.0,
            'dossiers': len(dossiers), 'dossiers_en_retard': sum(1 for r in retards if r > 0),
            'montant_en_retard': f(sum(retards, Decimal('0'))),
            'dossiers_sans_tarif': sum(1 for d in dossiers if d.montant_du == 0 and not d.montant_ajuste),
            'trop_percus': sum(1 for d in dossiers if d.trop_percu > 0),
            'montant_trop_percu': f(sum((d.trop_percu for d in dossiers), Decimal('0'))),
            'paie_en_attente': f(en_attente),
            'tresorerie': [{'mois': f'{a:04d}-{m:02d}', 'recettes': f(par_mois.get((a, m), (0, 0))[0]),
                            'depenses': f(par_mois.get((a, m), (0, 0))[1])} for a, m in mois],
        })


# ── Tarifs (Paramètres) ──────────────────────────────────────────

class TarifSerializer(serializers.ModelSerializer):
    parcours_code = serializers.CharField(source='parcours.code', read_only=True)
    annee_libelle = serializers.CharField(source='annee.libelle', read_only=True)
    echeancier = serializers.SerializerMethodField()

    class Meta:
        model = Tarif
        fields = ['id', 'annee', 'annee_libelle', 'parcours', 'parcours_code', 'montant', 'nombre_mensualites',
                  'premier_mois', 'jour_echeance', 'echeancier']
        extra_kwargs = {'premier_mois': {'required': False}}

    def get_echeancier(self, obj):
        return [{'mois': m, 'date_limite': d.isoformat(), 'montant': f(x)}
                for m, d, x in service_frais.echeancier(obj.montant, obj.nombre_mensualites, obj.premier_mois,
                                                        obj.jour_echeance)]


class TarifViewSet(viewsets.ModelViewSet):
    permission_classes = [Tarifs]
    serializer_class = TarifSerializer

    def get_queryset(self):
        qs = Tarif.objects.select_related('annee', 'parcours')
        annee = entier(self.request, 'annee')
        return qs.filter(annee_id=annee) if annee is not None else qs

    def perform_create(self, serializer):
        t = serializer.save()
        journaliser(self.request, 'parametres', 'tarif', f'Création : {t}')

    def perform_update(self, serializer):
        t = serializer.save()
        journaliser(self.request, 'parametres', 'tarif', f'Modification : {t}')

    def perform_destroy(self, instance):
        journaliser(self.request, 'parametres', 'tarif', f'Suppression : {instance}')
        instance.delete()


# ── Espace étudiant ──────────────────────────────────────────────

class MesFraisView(APIView):
    def get(self, request):
        from scolarite.views_etudiant import EstEtudiant
        if not EstEtudiant().has_permission(request, self):
            return Response({'detail': 'Réservé aux étudiants.'}, status=status.HTTP_403_FORBIDDEN)
        etudiant = request.user.personne.etudiant
        dossiers = (FraisScolarite.objects.filter(inscription__etudiant=etudiant)
                    .exclude(inscription__statut='abandonnee')
                    .select_related('inscription__etudiant__personne', 'inscription__classe', 'inscription__annee')
                    .order_by('-inscription__annee__date_debut'))
        donnees = []
        for d in dossiers:
            j = dossier_json(d, detail=True)
            j['paiements'] = [p for p in j['paiements'] if not p['annule']]
            donnees.append(j)
        return Response(donnees)


class MonRecuView(APIView):
    def get(self, request, pk):
        personne = getattr(request.user, 'personne', None)
        p = get_object_or_404(PaiementEtudiant.objects.select_related('operation'), pk=pk, annule=False,
                              dossier__inscription__etudiant__personne=personne)
        return reponse_pdf(recus.recu_paiement_etudiant(p), f'recu-{p.operation.numero}.pdf')


# ── Dépenses de transport ────────────────────────────────────────

def depense_json(d):
    from finance.models import DepenseTransport
    return {'id': d.pk, 'bus': d.bus_id, 'bus_numero': d.bus.numero, 'type': d.type,
            'type_libelle': dict(DepenseTransport.TYPES)[d.type], 'montant': f(d.montant), 'description': d.description,
            'date': d.date, 'numero': d.operation.numero, 'annule': d.annule, 'motif_annulation': d.motif_annulation}


class TransportViewSet(viewsets.ViewSet):
    permission_classes = [LectureFinance]

    def list(self, request):
        from core.pagination import PaginationStandard
        from finance.models import DepenseTransport
        qs = DepenseTransport.objects.select_related('bus', 'operation')
        bus = entier(request, 'bus')
        if bus is not None:
            qs = qs.filter(bus_id=bus)
        pagination = PaginationStandard()
        page = pagination.paginate_queryset(qs, request, view=self)
        return pagination.get_paginated_response([depense_json(d) for d in page])

    def create(self, request):
        from finance import transports
        from logistique.models import Bus
        bus = Bus.objects.filter(pk=entier_valeur(request.data.get('bus'))).first()
        if bus is None:
            raise ValidationError({'bus': 'Choisissez un bus.'})
        d = transports.enregistrer(bus, request.data.get('type'), request.data.get('montant'),
                                   date=_date(request.data.get('date')), description=request.data.get('description', ''),
                                   par=request.user)
        journaliser(request, 'finance', 'depense_transport', f'{d.operation.numero} — {d.operation.libelle} : {d.montant}')
        return Response(depense_json(d), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[ResponsableFinance])
    def annuler(self, request, pk=None):
        from finance import transports
        from finance.models import DepenseTransport
        d = get_object_or_404(DepenseTransport, pk=pk)
        contre = transports.annuler_depense(d, request.data.get('motif', ''), par=request.user)
        journaliser(request, 'finance', 'annulation_depense_transport', f'{contre.numero} — {contre.libelle}')
        return Response(operation_json(contre))


class RecuTransportView(APIView):
    permission_classes = [Encaissement]

    def get(self, request, pk):
        from finance.models import DepenseTransport
        d = get_object_or_404(DepenseTransport.objects.select_related('operation'), pk=pk)
        return reponse_pdf(recus.recu_operation(d.operation), f'recu-{d.operation.numero}.pdf')


def entier_valeur(valeur):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None
