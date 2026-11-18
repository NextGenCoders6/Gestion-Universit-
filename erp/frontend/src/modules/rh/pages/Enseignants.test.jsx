import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import Enseignants from './Enseignants';

vi.mock('../api');

function connecter(niveaux) {
  useAuthStore.getState().setAuth({ accessToken: 'a', refreshToken: 'r',
    user: { id: 1, username: 'u', nom_complet: 'U', roles: [], modules: [{ code: 'rh', niveaux }] } });
}

function rendre() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter><Enseignants /></MemoryRouter></QueryClientProvider>);
}

const LIGNE = { id: 3, matricule: 'UCCB-ENS-00003', nom_complet: 'MBEMBA Christelle', departement: 1,
  departement_libelle: 'Informatique', faculte: 'FST', grade: 'Docteur', est_chef: false,
  contrat_en_cours: { id: 9, type: 'vacataire', date_debut: '2026-09-01', date_fin: '2027-07-31' }, actif: true };

describe('RH — enseignants', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listerEnseignants.mockResolvedValue({ count: 1, results: [LIGNE] });
    api.listerDepartements.mockResolvedValue([{ id: 1, libelle: 'Informatique', faculte_code: 'FST' }]);
  });

  it('lecture seule pour rh_utilisateur', async () => {
    connecter(['utilisateur']);
    rendre();
    expect(await screen.findByText('MBEMBA Christelle')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Nouvel enseignant/ })).not.toBeInTheDocument();
  });

  it('ajout avec contrat : erreur du contrat renvoyée par le serveur affichée', async () => {
    connecter(['responsable']);
    api.creerEnseignant.mockRejectedValue({ response: { status: 400, data: {
      contrat: { date_debut: ['Ce contrat chevauche un autre contrat de la personne.'] } } } });
    const user = userEvent.setup();
    rendre();
    await user.click(await screen.findByRole('button', { name: /Nouvel enseignant/ }));
    const dialog = within(screen.getByRole('dialog'));
    await user.type(dialog.getByLabelText(/^Nom/), 'Moukoko');
    await user.type(dialog.getByLabelText(/^Prénom/), 'Albert');
    await user.selectOptions(dialog.getByLabelText(/^Genre/), 'M');
    await user.selectOptions(dialog.getByLabelText(/^Département/), '1');
    await user.selectOptions(dialog.getByLabelText(/^Type de contrat/), 'vacataire');
    await user.type(dialog.getByLabelText(/^Début du contrat/), '2026-09-01');
    await user.type(dialog.getByLabelText(/^Taux horaire/), '6000');
    await user.click(dialog.getByRole('button', { name: 'Enregistrer' }));
    await waitFor(() => expect(api.creerEnseignant).toHaveBeenCalled());
    expect(api.creerEnseignant.mock.calls[0][0]).toMatchObject({
      personne: { nom: 'Moukoko', prenom: 'Albert', genre: 'M' }, departement: 1,
      contrat: { type: 'vacataire', date_debut: '2026-09-01', taux_horaire: '6000', salaire_mensuel: null } });
    expect(await screen.findByText('Ce contrat chevauche un autre contrat de la personne.')).toBeInTheDocument();
  });
});
