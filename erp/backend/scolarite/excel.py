"""Export Excel d'une délibération."""
import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

ENTETES_FIN = ['Moyenne', 'Crédits', 'Décision', 'Mention']


def classeur_deliberation(classe, semestre, prog, lignes):
    """Classeur .xlsx (bytes) : une ligne par étudiant, moyennes d'UE, résultat et rang."""
    wb = Workbook()
    ws = wb.active
    ws.title = f'Délibération {semestre}'
    ws.append([f'Délibération — {classe.libelle} — {semestre}'])
    ws['A1'].font = Font(bold=True, size=13)
    ws.append([])
    entetes = ['Rang', 'Matricule', 'Nom et prénom'] + [ue.code for ue, _ in prog] + ENTETES_FIN
    ws.append(entetes)
    for cellule in ws[ws.max_row]:
        cellule.font = Font(bold=True, color='FFFFFF')
        cellule.fill = PatternFill('solid', fgColor='0B7A3E')
    for ligne in lignes:
        etudiant = ligne['inscription'].etudiant
        ws.append([ligne['rang'], etudiant.matricule, etudiant.personne.nom_complet]
                  + [b['moyenne_ue'] for b in ligne['ues']]
                  + [ligne['moyenne'], f"{ligne['credits_valides']}/{ligne['credits_totaux']}",
                     ligne['decision'], ligne['mention']])
    for colonne, largeur in (('A', 6), ('B', 22), ('C', 32)):
        ws.column_dimensions[colonne].width = largeur
    flux = io.BytesIO()
    wb.save(flux)
    return flux.getvalue()
