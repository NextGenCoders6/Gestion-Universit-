"""API de la faculté : saisie des notes, délibérations, promotion et orientation."""
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.filtres import entier
from core.audit import journaliser
from core.models import AnneeAcademique, Classe, Filiere, Parcours
from scolarite.excel import classeur_deliberation
from scolarite.inscriptions import inscrire
from scolarite.models import Inscription, Note, ResultatSemestre
from scolarite.moteur import deliberation, ligne_etudiant, programme
from scolarite.perimetre import restreindre_par_faculte
from scolarite.permissions import Faculte, Secretariat
from scolarite.serialisation import ligne_json, programme_json, resultat_json
from scolarite.views_secretariat import etudiants_du_perimetre, inscriptions_visibles

CHAMPS_SAISIE = {'devoir': 'note_devoir', 'session': 'note_session', 'sr': 'note_sr'}
CHAMPS_API = {v: k for k, v in CHAMPS_SAISIE.items()} | {'est_absent': 'absent'}


def classe_demandee(request, valeur=None):
    """Classe du périmètre désignée par `valeur` ou le paramètre ?classe= ; 400 si absente, 404 si hors périmètre."""
    pk = valeur if valeur is not None else entier(request, 'classe')
    if pk in (None, ''):
        raise ValidationError({'classe': 'Choisissez une classe.'})
    try:
        pk = int(pk)
    except (TypeError, ValueError):
        raise ValidationError({'classe': 'Valeur invalide : un identifiant numérique est attendu.'})
    qs = Classe.objects.select_related('annee', 'parcours', 'portail', 'filiere')
    return get_object_or_404(restreindre_par_faculte(qs, request.user), pk=pk)


def programme_ou_400(classe, semestre):
    try:
        return programme(classe, semestre)
    except ValueError as exc:
        raise ValidationError({'semestre': str(exc)})


def refuser_si_archivee(annee):
    if annee.statut == 'archivee':
        raise ValidationError({'detail': "L'année est archivée : plus aucune modification n'est possible."})


# ── Saisie des notes ─────────────────────────────────────────────

class SaisieView(APIView):
    permission_classes = [Faculte]

    def get(self, request):
        classe = classe_demandee(request)
        ec_id = entier(request, 'ec')
        ec = classe.ecs_au_programme().filter(pk=ec_id).first() if ec_id is not None else None
        if ec is None:
            raise ValidationError({'ec': "Choisissez un EC au programme de cette classe."})
        if classe.annee.statut != 'archivee':
            # Un EC ajouté au programme après les inscriptions reçoit ici ses lignes de notes.
            deja = set(Note.objects.filter(inscription__classe=classe, ec=ec).values_list('inscription_id', flat=True))
            manquantes = classe.inscriptions.exclude(statut='abandonnee').exclude(pk__in=deja)
            Note.objects.bulk_create([Note(inscription=i, ec=ec) for i in manquantes], ignore_conflicts=True)
        notes = (Note.objects.filter(inscription__classe=classe, ec=ec)
                 .exclude(inscription__statut='abandonnee')
                 .select_related('inscription__etudiant__personne')
                 .order_by('inscription__etudiant__personne__nom', 'inscription__etudiant__personne__prenom'))
        return Response({
            'classe': classe.pk, 'ec': {'id': ec.pk, 'code': ec.code, 'libelle': ec.libelle, 'credits': ec.credits},
            'archivee': classe.annee.statut == 'archivee',
            'deliberee': ResultatSemestre.objects.filter(inscription__classe=classe, semestre=ec.ue.semestre).exists(),
            'lignes': [{
                'note_id': n.pk, 'etudiant': n.inscription.etudiant_id, 'matricule': n.inscription.etudiant.matricule,
                'nom_complet': n.inscription.etudiant.personne.nom_complet,
                'devoir': _f(n.note_devoir), 'session': _f(n.note_session), 'sr': _f(n.note_sr),
                'absent': n.est_absent, 'moyenne': _f(n.moyenne),
            } for n in notes],
        })

    def post(self, request):
        lignes = request.data.get('notes')
        if not isinstance(lignes, list) or not lignes:
            raise ValidationError({'notes': 'Aucune note à enregistrer.'})
        ids = [l.get('note_id') for l in lignes if isinstance(l, dict)]
        qs = Note.objects.select_related('inscription__annee', 'inscription__classe__parcours', 'ec__ue')
        notes = {n.pk: n for n in restreindre_par_faculte(qs, request.user, prefixe='inscription__classe__')
                 .filter(pk__in=[i for i in ids if isinstance(i, int)])}
        # Un semestre délibéré est figé : ses notes ne changent qu'après réouverture de la délibération.
        deliberes = set(ResultatSemestre.objects.filter(inscription__in={n.inscription_id for n in notes.values()})
                        .values_list('inscription_id', 'semestre'))
        enregistrees, erreurs = 0, {}
        for ligne in lignes:
            if not isinstance(ligne, dict):
                continue
            note = notes.get(ligne.get('note_id'))
            cle = str(ligne.get('note_id'))
            if note is None:
                erreurs[cle] = {'detail': 'Note introuvable.'}
                continue
            if note.inscription.annee.statut == 'archivee':
                erreurs[cle] = {'detail': "L'année est archivée : la note ne peut plus changer."}
                continue
            if (note.inscription_id, note.ec.ue.semestre) in deliberes:
                erreurs[cle] = {'detail': f'Le {note.ec.ue.semestre} est déjà délibéré : rouvrez la délibération '
                                          f'pour modifier cette note.'}
                continue
            probleme = _appliquer(note, ligne)
            if probleme:
                erreurs[cle] = probleme
                continue
            try:
                with transaction.atomic():
                    note.save()
            except DjangoValidationError as exc:
                erreurs[cle] = {CHAMPS_API.get(k, 'detail'): ' '.join(v) for k, v in exc.message_dict.items()}
                note.refresh_from_db()
                continue
            enregistrees += 1
        if enregistrees:
            journaliser(request, 'scolarite', 'saisie_notes', f'{enregistrees} note(s) enregistrée(s)')
        return Response({'enregistrees': enregistrees, 'erreurs': erreurs}, status=200 if enregistrees else 400)


def _f(valeur):
    return None if valeur is None else float(valeur)


def _appliquer(note, ligne):
    """Recopie les valeurs de la ligne sur la note ; renvoie les erreurs de format par champ."""
    erreurs = {}
    for api, champ in CHAMPS_SAISIE.items():
        if api not in ligne:
            continue
        brute = ligne[api]
        if brute is None or (isinstance(brute, str) and not brute.strip()):
            setattr(note, champ, None)
            continue
        try:
            valeur = Decimal(str(brute).strip().replace(',', '.'))
            if not valeur.is_finite():
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            erreurs[api] = 'Saisissez un nombre entre 0 et 20.'
            continue
        if not 0 <= valeur <= 20:
            erreurs[api] = 'Une note est comprise entre 0 et 20.'
            continue
        setattr(note, champ, valeur.quantize(Decimal('0.01')))
    if 'absent' in ligne:
        note.est_absent = bool(ligne['absent'])
    return erreurs


# ── Relevé d'un étudiant ─────────────────────────────────────────

class NotesEtudiantView(APIView):
    """Résultats calculés (et délibérés) d'un étudiant pour une année ; lecture secrétariat et faculté."""

    permission_classes = [Secretariat]

    def get(self, request, pk):
        etudiant = get_object_or_404(etudiants_du_perimetre(request.user), pk=pk)
        inscriptions = inscriptions_visibles(etudiant, request.user)
        annee = entier(request, 'annee')
        if annee is not None:
            inscription = get_object_or_404(inscriptions, annee_id=annee)
        else:
            inscription = inscriptions.first()
        if inscription is None:
            return Response({'inscription': None, 'semestres': []})
        resultats = {r.semestre: r for r in inscription.resultats.all()}
        return Response({
            'inscription': inscription.pk, 'classe': inscription.classe.libelle, 'annee': inscription.annee.libelle,
            'semestres': [{'semestre': s, 'ligne': ligne_json(ligne_etudiant(inscription, s)),
                           'resultat': resultat_json(resultats.get(s))} for s in inscription.classe.semestres],
        })


# ── Délibération ─────────────────────────────────────────────────

def _deliberation_json(classe, semestre, prog, lignes):
    resultats = ResultatSemestre.objects.filter(inscription__classe=classe, semestre=semestre)
    dernier = resultats.order_by('-delibere_le').values_list('delibere_le', flat=True).first()
    return {
        'classe': classe.pk, 'classe_libelle': classe.libelle, 'semestre': semestre,
        'archivee': classe.annee.statut == 'archivee',
        'ues': programme_json(prog), 'lignes': [ligne_json(l) for l in lignes],
        'ecs_non_saisis': sum(len(l['ecs_non_saisis']) for l in lignes),
        'deliberee': dernier is not None, 'delibere_le': dernier,
    }


class DeliberationView(APIView):
    permission_classes = [Faculte]

    def get(self, request):
        classe = classe_demandee(request)
        semestre = request.query_params.get('semestre', '')
        prog = programme_ou_400(classe, semestre)
        return Response(_deliberation_json(classe, semestre, prog, deliberation(classe, semestre)))

    def post(self, request):
        classe = classe_demandee(request, request.data.get('classe'))
        semestre = request.data.get('semestre', '')
        prog = programme_ou_400(classe, semestre)
        refuser_si_archivee(classe.annee)
        lignes = deliberation(classe, semestre, enregistrer=True, par=request.user)
        journaliser(request, 'scolarite', 'deliberation', f'{classe} — {semestre} ({len(lignes)} étudiant(s))')
        return Response(_deliberation_json(classe, semestre, prog, lignes))


    def delete(self, request):
        """Rouvre la délibération : les résultats enregistrés sont retirés et les notes redeviennent modifiables."""
        classe = classe_demandee(request)
        semestre = request.query_params.get('semestre', '')
        prog = programme_ou_400(classe, semestre)
        refuser_si_archivee(classe.annee)
        nombre, _ = ResultatSemestre.objects.filter(inscription__classe=classe, semestre=semestre).delete()
        journaliser(request, 'scolarite', 'reouverture_deliberation', f'{classe} — {semestre} ({nombre} résultat(s))')
        return Response(_deliberation_json(classe, semestre, prog, deliberation(classe, semestre)))


class DeliberationExcelView(APIView):
    permission_classes = [Faculte]

    def get(self, request):
        classe = classe_demandee(request)
        semestre = request.query_params.get('semestre', '')
        prog = programme_ou_400(classe, semestre)
        contenu = classeur_deliberation(classe, semestre, prog, deliberation(classe, semestre))
        reponse = HttpResponse(contenu, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        nom = f'deliberation-{classe.parcours.code}-{(classe.portail or classe.filiere).code}-{semestre}.xlsx'
        reponse['Content-Disposition'] = f'attachment; filename="{nom}"'
        return reponse


# ── Promotion et orientation (passage à l'année suivante) ────────

def annee_suivante(annee):
    return AnneeAcademique.objects.filter(date_debut__gt=annee.date_debut).order_by('date_debut').first()


def _inscriptions_de(classe, ids):
    return {i.etudiant_id: i for i in classe.inscriptions.exclude(statut='abandonnee')
            .filter(etudiant_id__in=ids).select_related('etudiant__personne')}


def _passer(inscription, cible, suivante, ignores):
    """Inscrit l'étudiant dans `cible` et clôt son inscription ; ajoute à `ignores` sinon. Renvoie True si fait."""
    nom = inscription.etudiant.personne.nom_complet
    if Inscription.objects.filter(etudiant_id=inscription.etudiant_id, annee=suivante).exists():
        ignores.append({'etudiant': inscription.etudiant_id, 'nom_complet': nom,
                        'motif': f"{nom} est déjà inscrit pour l'année suivante."})
        return False
    manquants = [s for s in inscription.classe.semestres
                 if not inscription.resultats.filter(semestre=s).exists()]
    if manquants:
        ignores.append({'etudiant': inscription.etudiant_id, 'nom_complet': nom,
                        'motif': f"{nom} : résultats non délibérés pour {', '.join(manquants)}."})
        return False
    with transaction.atomic():
        inscrire(inscription.etudiant, cible, type='reinscription')
        inscription.statut = 'terminee'
        inscription.save()
    return True


def _ids(valeurs):
    try:
        return [int(v) for v in valeurs]
    except (TypeError, ValueError):
        raise ValidationError({'etudiants': 'Liste d’identifiants invalide.'})


def _resultats_par_inscription(inscriptions):
    par = {}
    for r in ResultatSemestre.objects.filter(inscription__in=inscriptions).order_by('semestre'):
        par.setdefault(r.inscription_id, []).append({'semestre': r.semestre, **resultat_json(r)})
    return par


def _candidats_json(classe):
    inscriptions = list(classe.inscriptions.exclude(statut='abandonnee')
                        .select_related('etudiant__personne').order_by('etudiant__personne__nom'))
    resultats = _resultats_par_inscription(inscriptions)
    return [{'etudiant': i.etudiant_id, 'inscription': i.pk, 'matricule': i.etudiant.matricule,
             'nom_complet': i.etudiant.personne.nom_complet, 'statut': i.statut,
             'resultats': resultats.get(i.pk, [])} for i in inscriptions]


def _cible_promotion(classe):
    """(année suivante, classe cible) d'une promotion ; ValidationError expliquée sinon."""
    parcours = classe.parcours
    if parcours.code == 'L1':
        raise ValidationError({'detail': "Le passage de L1 en L2 se fait par l'orientation (choix de filière)."})
    if parcours.niveau >= Parcours.NIVEAUX_MAX.get(parcours.type_parcours, 0):
        raise ValidationError({'detail': f'{parcours.code} termine le cycle : passez les étudiants au statut Diplômé.'})
    suivante = annee_suivante(classe.annee)
    if suivante is None:
        raise ValidationError({'detail': f"L'année suivant {classe.annee.libelle} n'est pas encore créée."})
    niveau = Parcours.objects.filter(type_parcours=parcours.type_parcours, niveau=parcours.niveau + 1).first()
    cible = Classe.objects.filter(annee=suivante, parcours=niveau, filiere_id=classe.filiere_id).first() \
        if niveau else None
    if cible is None:
        code = f'{Parcours.PREFIXES[parcours.type_parcours]}{parcours.niveau + 1}'
        raise ValidationError({'detail': f"La classe {code} {classe.filiere.code} de {suivante.libelle} n'existe pas : "
                                         f"créez-la dans Paramètres."})
    return suivante, cible


class PromotionView(APIView):
    permission_classes = [Faculte]

    def get(self, request):
        classe = classe_demandee(request)
        try:
            cible = _cible_promotion(classe)[1].pk
        except ValidationError:
            cible = None
        return Response({'classe': classe.pk, 'classe_cible': cible, 'etudiants': _candidats_json(classe)})

    def post(self, request):
        classe = classe_demandee(request, request.data.get('classe'))
        suivante, cible = _cible_promotion(classe)
        ids = _ids(request.data.get('etudiants') or [])
        inscriptions = _inscriptions_de(classe, ids)
        promus, ignores = 0, []
        for pk in ids:
            if pk not in inscriptions:
                ignores.append({'etudiant': pk, 'nom_complet': None, 'motif': "N'appartient pas à cette classe."})
            elif _passer(inscriptions[pk], cible, suivante, ignores):
                promus += 1
        journaliser(request, 'scolarite', 'promotion', f'{classe} → {cible} : {promus} promu(s)')
        return Response({'promus': promus, 'ignores': ignores, 'classe_cible': cible.pk})


class OrientationView(APIView):
    """L1 → L2 : chaque étudiant rejoint une filière issue du portail de sa L1."""

    permission_classes = [Faculte]

    def _classe_l1(self, request, valeur=None):
        classe = classe_demandee(request, valeur)
        if classe.parcours.code != 'L1':
            raise ValidationError({'classe': "L'orientation concerne les classes de L1."})
        return classe

    def get(self, request):
        classe = self._classe_l1(request)
        filieres = Filiere.objects.filter(portail_id=classe.portail_id).order_by('code')
        return Response({'classe': classe.pk, 'etudiants': _candidats_json(classe),
                         'filieres': [{'id': f.pk, 'code': f.code, 'nom': f.nom} for f in filieres]})

    def post(self, request):
        classe = self._classe_l1(request, request.data.get('classe'))
        suivante = annee_suivante(classe.annee)
        if suivante is None:
            raise ValidationError({'detail': f"L'année suivant {classe.annee.libelle} n'est pas encore créée."})
        choix = request.data.get('choix') or {}
        if not isinstance(choix, dict):
            raise ValidationError({'choix': 'Format attendu : {étudiant: filière}.'})
        ids = _ids(choix.keys())
        inscriptions = _inscriptions_de(classe, ids)
        l2 = Parcours.objects.filter(type_parcours='Licence', niveau=2).first()
        filieres = {f.pk: f for f in Filiere.objects.filter(pk__in=[v for v in choix.values() if isinstance(v, int)])}
        promus, ignores = 0, []
        for cle, filiere_id in choix.items():
            pk = int(cle)
            inscription = inscriptions.get(pk)
            filiere = filieres.get(filiere_id)
            if inscription is None:
                ignores.append({'etudiant': pk, 'nom_complet': None, 'motif': "N'appartient pas à cette classe."})
                continue
            nom = inscription.etudiant.personne.nom_complet
            if filiere is None or filiere.portail_id != classe.portail_id:
                ignores.append({'etudiant': pk, 'nom_complet': nom,
                                'motif': f"{nom} : la filière choisie n'est pas issue du portail {classe.portail.code}."})
                continue
            cible = Classe.objects.filter(annee=suivante, parcours=l2, filiere=filiere).first()
            if cible is None:
                ignores.append({'etudiant': pk, 'nom_complet': nom,
                                'motif': f"La classe L2 {filiere.code} de {suivante.libelle} n'existe pas."})
                continue
            if _passer(inscription, cible, suivante, ignores):
                promus += 1
        journaliser(request, 'scolarite', 'orientation', f'{classe} : {promus} orienté(s)')
        return Response({'promus': promus, 'ignores': ignores})
