import { expect, test } from '@playwright/test';

const MDP = 'Uccb!2026demo';

async function connecter(page, identifiant) {
  await page.goto('/login');
  await page.getByLabel('Identifiant').fill(identifiant);
  await page.getByLabel('Mot de passe', { exact: true }).fill(MDP);
  await page.getByRole('button', { name: 'Se connecter' }).click();
}

test('le responsable Paramètres crée une faculté', async ({ page }) => {
  await connecter(page, 'parametres');
  await expect(page.getByRole('heading', { name: 'Vos modules' })).toBeVisible();
  const tuiles = page.getByRole('main').getByRole('link');
  await expect(tuiles).toHaveCount(1);
  await tuiles.filter({ hasText: 'Paramètres' }).click();

  await page.getByRole('link', { name: 'Référentiel' }).click();
  await page.getByRole('tab', { name: 'Facultés' }).click();
  await page.getByRole('button', { name: /Nouvelle faculté/ }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Code').fill('FDR');
  await dialog.getByLabel('Nom', { exact: true }).fill('Faculté de Droit');
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('cell', { name: 'Faculté de Droit' })).toBeVisible();
});

test('un responsable RH ne peut pas ouvrir Paramètres', async ({ page }) => {
  await connecter(page, 'rh_responsable');
  await expect(page.getByRole('heading', { name: 'Vos modules' })).toBeVisible();
  await page.goto('/parametres/referentiel');
  await expect(page.getByText('Accès non autorisé')).toBeVisible();
  await expect(page).toHaveURL(/\/parametres\/referentiel$/);
});

test('un employé sans droit voit un lanceur vide', async ({ page }) => {
  await connecter(page, 'employe');
  await expect(page.getByText(/Aucun module ne vous est attribué/)).toBeVisible();
});

test('un compte suspendu en cours de session est renvoyé au login avec le motif', async ({ browser }) => {
  const admin = await (await browser.newContext()).newPage();
  const victime = await (await browser.newContext()).newPage();

  await connecter(victime, 'finance_utilisateur');
  await expect(victime.getByRole('heading', { name: 'Vos modules' })).toBeVisible();

  // Le compte finance_utilisateur n'a pas de fiche personne : on en lie une, puis on la suspend.
  await connecter(admin, 'parametres');
  await expect(admin.getByRole('heading', { name: 'Vos modules' })).toBeVisible();
  await admin.goto('/parametres/personnes');
  await admin.getByRole('button', { name: /Nouvelle personne/ }).click();
  let dialog = admin.getByRole('dialog');
  await dialog.getByLabel('Nom', { exact: true }).fill('Ibara');
  await dialog.getByLabel('Prénom').fill('Nadège');
  await dialog.getByLabel('Genre').selectOption('F');
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await expect(dialog).toBeHidden();

  await admin.goto('/parametres/utilisateurs');
  await admin.getByRole('row', { name: /finance_utilisateur/ }).getByRole('button', { name: /Modifier/ }).click();
  dialog = admin.getByRole('dialog');
  await dialog.getByLabel('Personne liée').selectOption({ label: 'IBARA Nadège' });
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await expect(dialog).toBeHidden();

  await admin.goto('/parametres/personnes');
  await admin.getByRole('row', { name: /IBARA Nadège/ }).getByRole('button').last().click();
  await admin.getByRole('menuitem', { name: 'Suspendre' }).click();
  dialog = admin.getByRole('dialog');
  await dialog.getByLabel('Motif').fill('Contrôle des accès');
  await dialog.getByRole('button', { name: 'Suspendre' }).click();
  await expect(dialog).toBeHidden();

  // Clic suivant de la victime : l'API refuse, retour au login avec le motif.
  await victime.getByRole('link', { name: /Finance/ }).click();
  await expect(victime).toHaveURL(/\/login$/);
  await expect(victime.getByText(/Contrôle des accès/)).toBeVisible();
});
