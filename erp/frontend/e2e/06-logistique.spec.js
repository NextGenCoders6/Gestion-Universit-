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

const demain = () => { const d = new Date(); d.setDate(d.getDate() + 1); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); };

test('maintenance, nouveau bus et affectation ; le même chauffeur est refusé ailleurs', async ({ page, request }) => {
  await connecter(page, 'logistique_responsable');
  await page.goto('/logistique/bus');

  // Bus 02 en maintenance : son affectation (Nzaba) se termine aujourd'hui.
  await page.getByRole('button', { name: 'Statut du bus 02' }).click();
  let dialog = page.getByRole('dialog');
  await dialog.getByLabel('Statut').selectOption({ label: 'Maintenance' });
  await expect(dialog.getByText(/sera terminée aujourd’hui/)).toBeVisible();
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await expect(page.getByText('1 affectation terminée.').first()).toBeVisible();

  await page.getByRole('button', { name: /Nouveau bus/ }).click();
  dialog = page.getByRole('dialog');
  await dialog.getByLabel('Numéro').fill('04');
  await dialog.getByLabel('Plaque').fill('CG-004-AA');
  await dialog.getByLabel('Capacité (places)').fill('40');
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await expect(page.getByRole('heading', { name: 'Bus 04' })).toBeVisible();

  await page.getByRole('link', { name: 'Affectations' }).click();
  await page.getByRole('button', { name: /Nouvelle affectation/ }).click();
  dialog = page.getByRole('dialog');
  await dialog.getByLabel('À partir du').fill(demain());
  await dialog.getByLabel('Bus').selectOption({ label: 'Bus 04 (CG-004-AA)' });
  await dialog.getByLabel('Chauffeur').selectOption({ label: 'NZABA Didier' });
  await dialog.getByLabel('Trajet').selectOption({ label: 'Retour du soir' });
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await expect(page.getByText('Affectation enregistrée').first()).toBeVisible();

  // Le même chauffeur sur un autre bus à la même date : refus explicite du serveur.
  const jeton = await page.evaluate(() => JSON.parse(localStorage.getItem('erp-auth')).state.accessToken);
  const entetes = { Authorization: `Bearer ${jeton}` };
  const bus = await (await request.get(`${API}/api/logistique/bus/`, { headers: entetes })).json();
  const chauffeurs = await (await request.get(`${API}/api/logistique/affectations/?actives=true`, { headers: entetes })).json();
  const trajets = await (await request.get(`${API}/api/logistique/trajets/`, { headers: entetes })).json();
  const malonga = (await (await request.get(`${API}/api/logistique/affectations/`, { headers: entetes })).json())
    .results.find((a) => a.chauffeur_nom === 'NZABA Didier' && a.bus_numero === '04');
  const bus01 = bus.results.find((b) => b.numero === '01');
  expect(chauffeurs.count).toBeGreaterThan(0);
  const r = await request.post(`${API}/api/logistique/affectations/`, { headers: entetes, data: {
    bus: bus01.id, chauffeur: malonga.chauffeur, trajet: trajets.results[0].id, date_debut: demain() } });
  expect(r.status()).toBe(400);
  expect(JSON.stringify(await r.json())).toMatch(/bus|chauffeur/);
});

test('une dépense de carburant saisie par la Finance apparaît dans les coûts de la Logistique', async ({ page, browser }) => {
  await connecter(page, 'finance_responsable');
  await page.goto('/finance/transports');
  await page.getByRole('button', { name: /Nouvelle dépense/ }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Bus').selectOption({ label: 'Bus 04 (CG-004-AA)' });
  await dialog.getByLabel('Type').selectOption({ label: 'Carburant' });
  await dialog.getByLabel('Montant (FCFA)').fill('42000');
  await dialog.getByRole('button', { name: 'Enregistrer' }).click();
  await expect(page.getByText('Dépense enregistrée').first()).toBeVisible();

  const logistique = await (await browser.newContext()).newPage();
  await connecter(logistique, 'logistique_utilisateur');
  await logistique.goto('/logistique/couts');
  await expect(logistique.getByText('Bus 04')).toBeVisible();
  await expect(logistique.getByText(/42\s000 FCFA/).first()).toBeVisible();
});
