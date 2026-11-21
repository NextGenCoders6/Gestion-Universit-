from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance'
    verbose_name = 'Finance'

    def ready(self):
        from core.lanceur import enregistrer
        from finance.lanceur import resume as resume_lanceur
        enregistrer('finance', resume_lanceur)

        from finance.frais import creer_dossier
        from scolarite import inscriptions
        if creer_dossier not in inscriptions.APRES_INSCRIPTION:
            inscriptions.APRES_INSCRIPTION.append(creer_dossier)

        from finance.paie import creer_ligne_vacation, refuser_retrait_si_payee
        from rh import vacations
        if creer_ligne_vacation not in vacations.APRES_CONFIRMATION:
            vacations.APRES_CONFIRMATION.append(creer_ligne_vacation)
        if refuser_retrait_si_payee not in vacations.VERIFICATIONS_RETRAIT:
            vacations.VERIFICATIONS_RETRAIT.append(refuser_retrait_si_payee)

        from finance.frais import motif_masquage_resultats
        from scolarite import inscriptions as scol
        if motif_masquage_resultats not in scol.MOTIFS_MASQUAGE_RESULTATS:
            scol.MOTIFS_MASQUAGE_RESULTATS.append(motif_masquage_resultats)

        from finance.frais import recalculer_dossier
        if recalculer_dossier not in scol.APRES_CHANGEMENT_CLASSE:
            scol.APRES_CHANGEMENT_CLASSE.append(recalculer_dossier)
