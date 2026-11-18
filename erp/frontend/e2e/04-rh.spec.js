import { expect, test } from '@playwright/test';

const MDP = 'Uccb!2026demo';

async function connecter(page, identifiant) {
  await page.goto('/login');
  await page.getByLabel('Identifiant').fill(identifiant);
  await page.getByLabel('Mot de passe', { exact: true }).fill(MDP);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await expect(page.getByRole('heading', { name: 'Vos modules' })).toBeVisible();
}

test('la RH ajoute un enseignant vacataire avec son contrat', async ({ page }) => {
  await connecter(page, 'rh_responsable');
  await page.getByRole('main').getByRole('link', { name: /Ressources humaines/ }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Tableau de bord' })).toBeVisible();
  await page.getByRole('link', { name: 'Enseignants', exact: true }).click();
  await page.getByRole('button', { name: /Nouvel enseignant/ }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Nom', { exact: true }).fill('Moukoko');
  await dialog.getByLabel('Prénom').fill('Albert');
  await dialog.getByLabel('Genre').selectOption({ label: 'Masculin' });
  await dialog.getByLabel('Département').selectOption({ label: 'Informatique (FST)' });
  await dialog.getByLabel('Type de contrat').selectOption({ label: 'Vacataire' });
  await dialog.getByLabel('Début du contrat').fill('2026-11-01');
  await dialog.getByLabel('Fin du contrat').fill('2027-07-31');
  await dialog.getByLabel('Taux horaire (FCFA)').fill('6000');
  await dialog.getByLabel('RIB').fill('CG39 3001 0000 9999 4321');
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'MOUKOKO Albert' })).toBeVisible();
  await expect(page.getByText(/Vacataire jusqu’au 31\/07\/2027/).first()).toBeVisible();
  await expect(page.getByText(/RIB CG39 3001 0000 9999 4321/)).toBeVisible();
});

test("rh_utilisateur voit le RIB masqué et ne peut rien modifier", async ({ page }) => {
  await connecter(page, 'rh_utilisateur');
  await page.goto('/rh/enseignants?q=Moukoko');
  await page.getByRole('button', { name: 'Actions pour MOUKOKO Albert' }).click();
  await page.getByRole('menuitem', { name: 'Ouvrir la fiche' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'MOUKOKO Albert' })).toBeVisible();
  await expect(page.getByText(/RIB •••• 4321/)).toBeVisible();
  await expect(page.getByText(/CG39 3001/)).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Nouveau contrat/ })).toHaveCount(0);
});

test('la faculté confirme une vacation terminée ; la RH la voit dans l’historique', async ({ page, browser }) => {
  await connecter(page, 'scolarite_faculte');
  await page.goto('/scolarite/vacations');
  const ligne = page.getByRole('row', { name: /NKOUNKOU Arsène.*SYSEXP/ });
  await ligne.getByRole('button', { name: 'Confirmer' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('button', { name: 'Confirmer la vacation' }).click();
  await expect(page.getByText('Vacation confirmée').first()).toBeVisible();

  // Autre compte : nouveau contexte (la page de connexion redirige un utilisateur déjà connecté).
  const rh = await (await browser.newContext()).newPage();
  await connecter(rh, 'rh_utilisateur');
  await rh.goto('/rh/vacations');
  await rh.getByRole('tab', { name: 'Historique' }).click();
  await expect(rh.getByText(/Confirmation · NKOUNKOU Arsène · SYSEXP/)).toBeVisible();
});
