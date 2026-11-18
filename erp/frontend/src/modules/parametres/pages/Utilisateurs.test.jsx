import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../api';
import Utilisateurs from './Utilisateurs';

vi.mock('../api');

const MODULES = [
  { code: 'scolarite', libelle: 'Scolarité', niveaux: ['secretariat', 'faculte'] },
  { code: 'rh', libelle: 'Ressources humaines', niveaux: ['utilisateur', 'responsable'] },
];

function rendre() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter><Utilisateurs /></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Paramètres — Utilisateurs', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listerModules.mockResolvedValue(MODULES);
    api.lister.mockImplementation((ressource) => Promise.resolve(
      ressource === 'facultes' ? [{ id: 1, code: 'FST', nom: 'Sciences' }]
        : ressource === 'personnes' ? [{ id: 7, nom_complet: 'NGOMA Paul' }]
          : [],
    ));
    api.listerUtilisateurs.mockResolvedValue([]);
    api.creerUtilisateur.mockResolvedValue({ id: 3 });
  });

  it('envoie les groupes choisis et la faculté de rattachement', async () => {
    const user = userEvent.setup();
    rendre();
    await user.click(await screen.findByRole('button', { name: /Nouvel utilisateur/ }));
    const dialog = await screen.findByRole('dialog');
    await user.type(within(dialog).getByLabelText('Identifiant'), 'p.ngoma');
    await user.type(within(dialog).getByLabelText('Mot de passe'), 'Uccb!2026demo');
    await user.selectOptions(within(dialog).getByLabelText('Ressources humaines'), 'responsable');
    await user.selectOptions(within(dialog).getByLabelText('Scolarité'), 'faculte');
    await user.selectOptions(await within(dialog).findByLabelText('Faculté de rattachement'), '1');
    await user.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));

    await waitFor(() => expect(api.creerUtilisateur).toHaveBeenCalled());
    const envoi = api.creerUtilisateur.mock.calls[0][0];
    expect([...envoi.groupes].sort()).toEqual(['rh_responsable', 'scolarite_faculte']);
    expect(envoi.faculte_rattachee_id).toBe(1);
    expect(envoi.username).toBe('p.ngoma');
  });

  it('cache la faculté de rattachement sans droit Scolarité', async () => {
    const user = userEvent.setup();
    rendre();
    await user.click(await screen.findByRole('button', { name: /Nouvel utilisateur/ }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).queryByLabelText('Faculté de rattachement')).not.toBeInTheDocument();
  });

  it('affiche l’erreur de champ renvoyée par le serveur', async () => {
    api.creerUtilisateur.mockRejectedValue({ response: { status: 400, data: { password: ['Ce mot de passe est trop court.'] } } });
    const user = userEvent.setup();
    rendre();
    await user.click(await screen.findByRole('button', { name: /Nouvel utilisateur/ }));
    const dialog = await screen.findByRole('dialog');
    await user.type(within(dialog).getByLabelText('Identifiant'), 'x');
    await user.type(within(dialog).getByLabelText('Mot de passe'), '12');
    await user.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));
    expect(await within(dialog).findByText('Ce mot de passe est trop court.')).toBeInTheDocument();
  });
});
