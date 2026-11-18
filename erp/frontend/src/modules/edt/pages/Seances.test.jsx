import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import Seances from './Seances';

vi.mock('../api');

const SEANCES = [
  { id: 1, ec: 5, ec_code: 'BDD', ec_libelle: 'Bases de données', classe: 2, classe_libelle: 'L2 INFO', enseignant: 9,
    enseignant_nom: 'MBEMBA C.', type_seance: 'CM', statut: 'brouillon', date_seance: '2026-10-05',
    heure_debut: '09:00', heure_fin: '11:00', seance_liee: null,
    creneau_effectif: { jour: '2026-10-05', debut: '09:00', fin: '11:00' } },
  { id: 2, ec: 5, ec_code: 'BDD', ec_libelle: 'Bases de données', classe: 2, classe_libelle: 'L2 INFO', enseignant: 9,
    enseignant_nom: 'MBEMBA C.', type_seance: 'TD', statut: 'Confirmée', date_seance: '2026-10-06',
    heure_debut: '09:00', heure_fin: '11:00', seance_liee: null,
    creneau_effectif: { jour: '2026-10-06', debut: '09:00', fin: '11:00' } },
];

function connecter(niveaux) {
  useAuthStore.getState().setAuth({
    accessToken: 'a', refreshToken: 'r',
    user: { id: 1, username: 'u', nom_complet: 'U', roles: [], modules: [{ code: 'edt', niveaux }] },
  });
}

function rendre() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter><Seances /></MemoryRouter></QueryClientProvider>);
}

describe('EDT — Séances', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listerSeances.mockResolvedValue(SEANCES);
    api.listerEnseignements.mockResolvedValue({ results: [] });
    api.listerEnseignants.mockResolvedValue([]);
    api.anneeEnCours.mockResolvedValue({ id: 1, libelle: '2026-2027' });
  });

  it('lecture seule pour edt_utilisateur : ni création ni publication', async () => {
    connecter(['utilisateur']);
    rendre();
    expect(await screen.findAllByText('Bases de données')).toHaveLength(2);
    expect(screen.queryByRole('button', { name: /Nouvelle séance/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Publier/ })).not.toBeInTheDocument();
  });

  it('un gestionnaire publie les brouillons sélectionnés', async () => {
    connecter(['perimetre']);
    api.publierEnMasse.mockResolvedValue({ detail: '1 séance(s) publiée(s).' });
    const user = userEvent.setup();
    rendre();
    await screen.findAllByText('Bases de données');
    expect(screen.getByRole('button', { name: /Nouvelle séance/ })).toBeInTheDocument();
    await user.click(screen.getByRole('checkbox', { name: /Sélectionner la séance du 05\/10\/2026/ }));
    await user.click(screen.getByRole('button', { name: /Publier la sélection/ }));
    await waitFor(() => expect(api.publierEnMasse).toHaveBeenCalledWith([1]));
  });

  it('affiche les erreurs de publication en masse', async () => {
    connecter(['responsable']);
    api.publierEnMasse.mockRejectedValue({ response: { status: 400, data: {
      detail: "Impossible de publier l'emploi du temps en raison de conflits.",
      erreurs: ['Le 05/10/2026 (BDD, L2 INFO) : La classe a déjà une séance le 05/10/2026 sur ce créneau.'] } } });
    const user = userEvent.setup();
    rendre();
    await screen.findAllByText('Bases de données');
    await user.click(screen.getByRole('checkbox', { name: /Sélectionner la séance du 05\/10\/2026/ }));
    await user.click(screen.getByRole('button', { name: /Publier la sélection/ }));
    const alerte = await screen.findByRole('alert');
    expect(within(alerte).getByText(/La classe a déjà une séance/)).toBeInTheDocument();
  });
});
