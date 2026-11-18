"""Paiements des frais de scolarité, annulations et opérations manuelles du journal."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from finance import journal
from finance.models import FraisScolarite, Operation, PaiementEtudiant


def libelle_dossier(dossier):
    i = dossier.inscription
    return f'Frais de scolarité — {i.etudiant.personne.nom_complet} ({i.etudiant.matricule}), {i.classe.libelle}'


@transaction.atomic
def encaisser(dossier, montant, mode, *, date=None, reference='', par=None):
    montant = journal.montant_valide(montant)
    mode = journal.mode_valide(mode)
    jour = journal.date_valide(date)
    # Verrou : deux encaissements simultanés ne dépassent jamais le reste dû.
    dossier = (FraisScolarite.objects.select_for_update()
               .select_related('inscription__etudiant__personne', 'inscription__classe').get(pk=dossier.pk))
    if dossier.reste <= 0:
        raise ValidationError({'montant': 'Ce dossier est déjà soldé (ou sans montant dû).'})
    if montant > dossier.reste:
        raise ValidationError({'montant': f'Le montant dépasse le reste dû ({dossier.reste:.0f} FCFA).'})
    operation = journal.ecrire(libelle_dossier(dossier), montant, 'frais', jour, par)
    paiement = PaiementEtudiant.objects.create(dossier=dossier, montant=montant, mode=mode, date=jour,
                                               reference=(reference or '')[:60], operation=operation, par=par)
    FraisScolarite.objects.filter(pk=dossier.pk).update(montant_paye=F('montant_paye') + montant)
    return paiement


@transaction.atomic
def annuler_paiement(paiement, motif, par=None):
    motif = (motif or '').strip()
    if not motif:
        raise ValidationError({'motif': "Indiquez le motif de l'annulation."})
    paiement = PaiementEtudiant.objects.select_for_update().select_related('operation').get(pk=paiement.pk)
    if paiement.annule:
        raise ValidationError('Ce paiement est déjà annulé.')
    FraisScolarite.objects.select_for_update().get(pk=paiement.dossier_id)
    contre = journal.ecrire(f'Annulation — {paiement.operation.libelle} ({motif})', -paiement.montant, 'annulation',
                            timezone.localdate(), par, annule=paiement.operation)
    paiement.annule = True
    paiement.motif_annulation = motif[:255]
    paiement.save(update_fields=['annule', 'motif_annulation'])
    FraisScolarite.objects.filter(pk=paiement.dossier_id).update(montant_paye=F('montant_paye') - paiement.montant)
    return contre


@transaction.atomic
def operation_manuelle(libelle, montant, date=None, par=None):
    libelle = (libelle or '').strip()
    if not libelle:
        raise ValidationError({'libelle': 'Indiquez le libellé.'})
    montant = journal.montant_valide(montant, positif=False)
    if montant == 0:
        raise ValidationError({'montant': 'Le montant ne peut pas être nul (+ recette, − dépense).'})
    return journal.ecrire(libelle, montant, 'manuelle', journal.date_valide(date), par)


@transaction.atomic
def annuler_operation(operation, motif, par=None):
    """Contre-écriture d'une opération manuelle (les paiements s'annulent par leur propre annulation)."""
    motif = (motif or '').strip()
    if not motif:
        raise ValidationError({'motif': "Indiquez le motif de l'annulation."})
    operation = Operation.objects.select_for_update().get(pk=operation.pk)
    if operation.categorie != 'manuelle':
        raise ValidationError("Seule une opération manuelle s'annule ici ; annulez le paiement correspondant.")
    if Operation.objects.filter(annule=operation).exists():
        raise ValidationError('Cette opération est déjà annulée.')
    return journal.ecrire(f'Annulation — {operation.libelle} ({motif})', -operation.montant, 'annulation',
                          timezone.localdate(), par, annule=operation)
