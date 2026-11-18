import { expect, test } from '@playwright/test';

const MDP = 'Uccb!2026demo';

async function connecter(page, identifiant) {
  await page.goto('/login');
  await page.getByLabel('Identifiant').fill(identifiant);
  await page.getByLabel('Mot de passe', { exact: true }).fill(MDP);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await expect(page.getByRole('heading', { name: 'Vos modules' })).toBeVisible();
}

async function nouvellePage(browser, identifiant) {
  const page = await (await browser.newContext()).newPage();
  await connecter(page, identifiant);
  return page;
}

test('Paramètres crée le tarif M1 : le dossier de M1 est recalculé avec son échéancier', async ({ page, browser }) => {
  await connecter(page, 'parametres');
  await page.goto('/parametres/tarifs');
  await page.getByRole('button', { name: /Nouveau tarif/ }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Année', { exact: true }).selectOption({ label: '2026-2027' });
  await dialog.getByLabel('Niveau').selectOption({ label: 'M1' });
  await dialog.getByLabel('Montant de l’année (FCFA)').fill('1800000');
  await expect(dialog.getByText(/10 mensualités de 180\s000 FCFA/)).toBeVisible();
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await expect(page.getByText('Tarif enregistré').first()).toBeVisible();

  const finance = await nouvellePage(browser, 'finance_utilisateur');
  await finance.goto('/finance/frais?q=Mavoungou');
  await expect(finance.getByText(/sur 1\s800\s000 FCFA/)).toBeVisible();
});

test('la caisse encaisse un paiement partiel, le reçu se télécharge et le journal montre la ligne', async ({ page }) => {
  await connecter(page, 'finance_utilisateur');
  await page.goto('/finance/frais?q=Mavoungou');
  await page.getByRole('button', { name: /Actions pour MAVOUNGOU Prisca/ }).click();
  await page.getByRole('menuitem', { name: 'Ouvrir le dossier' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'MAVOUNGOU Prisca' })).toBeVisible();

  await page.getByRole('button', { name: 'Encaisser un paiement' }).click();
  let dialog = page.getByRole('dialog');
  await dialog.getByLabel('Montant (FCFA)').fill('99999999');
  await dialog.getByLabel('Mode de paiement').selectOption({ label: 'Mobile Money' });
  await dialog.getByRole('button', { name: 'Encaisser' }).click();
  await expect(dialog.getByText(/dépasse le reste dû/)).toBeVisible();
  await dialog.getByLabel('Montant (FCFA)').fill('180000');
  await dialog.getByRole('button', { name: 'Encaisser' }).click();
  await expect(page.getByText('Paiement enregistré').first()).toBeVisible();
  await expect(page.getByRole('row', { name: /2026-10/ }).getByText('Payée')).toBeVisible();

  const telechargement = page.waitForEvent('download');
  await page.getByRole('button', { name: /Reçu/ }).first().click();
  expect((await telechargement).suggestedFilename()).toMatch(/^recu-OP-\d{4}-\d{6}\.pdf$/);

  await page.goto('/finance/journal');
  await page.getByLabel('Rechercher').fill('Mavoungou');
  await expect(page.getByText(/Frais de scolarité — MAVOUNGOU Prisca/)).toBeVisible();
});

test('le responsable génère la paie du mois et paie la vacation confirmée par la faculté', async ({ page }) => {
  await connecter(page, 'finance_responsable');
  await page.goto('/finance/paie-enseignants');
  await page.getByLabel('Mois').fill('2026-11');
  await page.getByRole('button', { name: 'Générer la paie' }).click();
  await expect(page.getByText(/Paie de 2026-11/).first()).toBeVisible();

  await page.getByLabel('Origine').selectOption({ label: 'Vacations' });
  const ligne = page.getByRole('row', { name: /NKOUNKOU Arsène.*SYSEXP/ });
  await ligne.getByRole('button', { name: 'Payer' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Montant (FCFA)').fill('22000');
  await dialog.getByLabel('Mode de paiement').selectOption({ label: 'Espèces' });
  await dialog.getByRole('button', { name: 'Payer' }).click();
  await expect(page.getByText('Paiement enregistré').first()).toBeVisible();
  await expect(ligne.getByText('Payée')).toBeVisible();
});

test("l'étudiant voit son échéancier et sa prochaine échéance", async ({ page }) => {
  await connecter(page, 'etudiant');
  await page.goto('/moi/frais');
  await expect(page.getByRole('heading', { level: 1, name: 'Mes frais' })).toBeVisible();
  await expect(page.getByText(/Prochaine échéance/)).toBeVisible();
  await expect(page.getByRole('cell', { name: '2026-10' })).toBeVisible();
});
