import { expect, test } from '@playwright/test';

const MDP = 'Uccb!2026demo';

async function connecter(page, identifiant) {
  await page.goto('/login');
  await page.getByLabel('Identifiant').fill(identifiant);
  await page.getByLabel('Mot de passe', { exact: true }).fill(MDP);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await expect(page.getByRole('heading', { name: 'Vos modules' })).toBeVisible();
}

test('le référent crée puis publie une séance de L1 MIP', async ({ page }) => {
  await connecter(page, 'referent');
  await page.getByRole('main').getByRole('link', { name: /Emploi du temps/ }).click();
  await page.getByRole('link', { name: 'Séances' }).click();
  await page.getByRole('button', { name: /Nouvelle séance/ }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Classe').selectOption({ label: 'L1 MIP — 2026-2027' });
  await dialog.getByLabel('Élément constitutif').selectOption({ label: 'PROG1 — Programmation 1 (S1)' });
  await dialog.getByLabel('Enseignant').selectOption({ label: 'NKOUNKOU Arsène (Informatique)' });
  await dialog.getByLabel('Date').fill('2026-11-07');           // un samedi libre
  await dialog.getByLabel('Début').fill('09:00');
  await dialog.getByLabel('Fin').fill('11:00');
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await expect(dialog).toBeHidden();

  await page.getByRole('checkbox', { name: 'Sélectionner la séance du 07/11/2026' }).check();
  await page.getByRole('button', { name: /Publier la sélection/ }).click();
  await expect(page.getByText(/1 séance\(s\) publiée\(s\)/).first()).toBeVisible();
});

test('le chef Informatique ne voit pas les classes de L1', async ({ page }) => {
  await connecter(page, 'chef');
  await page.goto('/edt/seances');
  const classes = page.getByLabel('Classe');
  await expect(classes.locator('option', { hasText: 'L2 INFO' })).toHaveCount(1);
  await expect(classes.locator('option', { hasText: 'L1 MIP' })).toHaveCount(0);
});

test("l'enseignante voit ses séances dans Mon espace", async ({ page, request }) => {
  await connecter(page, 'enseignant');
  await page.getByRole('main').getByRole('link', { name: /Mon espace/ }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Mon planning' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Semaine suivante' })).toBeVisible();
  // La grille affiche la semaine courante ; les séances de démonstration sont en octobre 2026 :
  // on vérifie qu'elles sont bien servies à l'enseignante par l'API du planning personnel.
  const jeton = await page.evaluate(() => JSON.parse(localStorage.getItem('erp-auth')).state.accessToken);
  const r = await request.get('http://127.0.0.1:8011/api/edt/moi/planning/?date_debut=2026-10-05&date_fin=2026-10-10',
    { headers: { Authorization: `Bearer ${jeton}` } });
  const seances = await r.json();
  expect(seances.some((x) => x.ec_code === 'ALGO1')).toBe(true);
  expect(seances.every((x) => x.enseignant_nom === 'MBEMBA Christelle')).toBe(true);
  await page.getByRole('link', { name: 'Mes enseignements' }).click();
  await expect(page.getByText(/BDD — Bases de données/)).toBeVisible();
});

test('déplacer une séance sur un dimanche est refusé avec un message', async ({ page, request }) => {
  await connecter(page, 'chef');
  // Le glisser-déposer est simulé par l'appel que fait le planning (même API, même message).
  const jeton = await page.evaluate(() => JSON.parse(localStorage.getItem('erp-auth')).state.accessToken);
  const entetes = { Authorization: `Bearer ${jeton}` };
  const liste = await (await request.get('http://127.0.0.1:8011/api/edt/seances/?statut=brouillon', { headers: entetes })).json();
  const id = liste.results[0].id;
  const r = await request.patch(`http://127.0.0.1:8011/api/edt/seances/${id}/`, {
    headers: entetes, data: { date_seance: '2026-11-01', heure_debut: '09:00', heure_fin: '11:00' },
  });
  expect(r.status()).toBe(400);
  expect((await r.json()).date_seance[0]).toContain('dimanche');
});
