import { expect, test } from '@playwright/test';

const MDP = 'Uccb!2026demo';
const API = 'http://127.0.0.1:8011';

async function connecter(page, identifiant) {
  await page.goto('/login');
  await page.getByLabel('Identifiant').fill(identifiant);
  await page.getByLabel('Mot de passe', { exact: true }).fill(MDP);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await expect(page.getByRole('heading', { name: 'Vos modules' })).toBeVisible();
}

const jeton = (page) => page.evaluate(() => JSON.parse(localStorage.getItem('erp-auth')).state.accessToken);

test("le secrétariat inscrit un étudiant et télécharge son attestation", async ({ page }) => {
  await connecter(page, 'scolarite_secretariat');
  await page.getByRole('main').getByRole('link', { name: /Scolarité/ }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Étudiants' })).toBeVisible();
  await page.getByRole('button', { name: /Nouvel étudiant/ }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Nom', { exact: true }).fill('Kouka');
  await dialog.getByLabel('Prénom').fill('Ange');
  await dialog.getByLabel('Genre').selectOption({ label: 'Féminin' });
  await dialog.getByLabel('Date de naissance').fill('2007-02-03');
  await dialog.getByLabel('E-mail').fill('ange.kouka@etu.uccb.cg');
  await dialog.getByLabel('Classe').selectOption({ label: 'L1 MIP — 2026-2027' });
  await dialog.getByRole('button', { name: 'Inscrire' }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'KOUKA Ange' })).toBeVisible();
  await expect(page.getByText(/Matricule UCCB26KOUAN\d+ · compte non activé/)).toBeVisible();

  const telechargement = page.waitForEvent('download');
  await page.getByRole('button', { name: /Attestation PDF/ }).click();
  expect((await telechargement).suggestedFilename()).toMatch(/^attestation-UCCB26KOUAN\d+\.pdf$/);
});

test('la faculté saisit des notes (cellule invalide signalée) puis délibère', async ({ page }) => {
  await connecter(page, 'scolarite_faculte');
  await page.goto('/scolarite/saisie');
  await page.getByLabel('Classe').selectOption({ label: 'L1 MIP — 2026-2027' });
  await page.getByLabel('Élément constitutif').selectOption({ label: 'S1 · ALGO1 — Algorithmique 1' });
  const devoirs = page.getByRole('textbox', { name: /^Devoir — / });
  await expect(devoirs.first()).toBeVisible();
  await devoirs.nth(0).fill('25');
  await devoirs.nth(1).fill('14');
  await page.getByRole('button', { name: /Enregistrer/ }).click();
  await expect(page.getByText('Une note est comprise entre 0 et 20.')).toBeVisible();
  await expect(devoirs.nth(0)).toHaveValue('25');
  await expect(page.getByText('1 note(s) enregistrée(s)').first()).toBeVisible();

  await page.getByRole('link', { name: 'Délibérations' }).click();
  await page.getByLabel('Classe').selectOption({ label: 'L1 MIP — 2026-2027' });
  await page.getByLabel('Semestre').selectOption('S1');
  await page.getByRole('button', { name: /Enregistrer la délibération/ }).click();
  await page.getByRole('alertdialog').getByRole('button', { name: 'Enregistrer' }).click();
  await expect(page.getByText('Délibération enregistrée').first()).toBeVisible();
});

test("l'étudiant voit la décision de son semestre", async ({ page }) => {
  await connecter(page, 'etudiant');
  await page.getByRole('main').getByRole('link', { name: /Mon espace/ }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Mes notes' })).toBeVisible();
  await expect(page.getByText(/(ADMIS|AJOURNÉ)/).first()).toBeVisible();
  await expect(page.getByText(/crédits/).first()).toBeVisible();
});

test("la page de vérification d'un document s'ouvre ; un jeton modifié est introuvable", async ({ page, request }) => {
  await connecter(page, 'scolarite_secretariat');
  const entetes = { Authorization: `Bearer ${await jeton(page)}` };
  const liste = await (await request.get(`${API}/api/scolarite/etudiants/?q=Kouka`, { headers: entetes })).json();
  const r = await request.get(`${API}/api/scolarite/etudiants/${liste.results[0].id}/attestation.pdf`, { headers: entetes });
  expect(r.ok()).toBeTruthy();
  const url = r.headers()['x-verification-url'];
  expect(url).toMatch(/\/verifier\/[\w-]{32}$/);

  await page.goto(url);
  await expect(page.getByRole('heading', { name: /Document authentique/ })).toBeVisible();
  await expect(page.getByText('KOUKA Ange')).toBeVisible();

  const dernier = url.slice(-1);
  await page.goto(url.slice(0, -1) + (dernier === 'A' ? 'B' : 'A'));
  await expect(page.getByRole('heading', { name: /Document introuvable/ })).toBeVisible();
  await expect(page.getByText('KOUKA Ange')).toHaveCount(0);
});
