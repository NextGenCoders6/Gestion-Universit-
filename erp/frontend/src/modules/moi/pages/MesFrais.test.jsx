import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../api';
import MesFrais from './MesFrais';
import MesNotes from './MesNotes';

vi.mock('../api');

function rendre(element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{element}</QueryClientProvider>);
}

describe('Espace étudiant — frais', () => {
  beforeEach(() => vi.resetAllMocks());

  it('échéancier, retard et reçus', async () => {
    api.mesFrais.mockResolvedValue([{ id: 1, annee_libelle: '2026-2027', classe_libelle: 'L1 MIP — 2026-2027',
      montant_du: 1500000, montant_paye: 75000, reste: 1425000, en_retard: true, montant_en_retard: 75000, statut: 'partiel',
      prochaine_echeance: { numero: 1, mois: '2026-10', date_limite: '2026-11-05', montant: 150000, paye: 75000, etat: 'en_retard' },
      echeances: [{ numero: 1, mois: '2026-10', date_limite: '2026-11-05', montant: 150000, paye: 75000, etat: 'en_retard' }],
      paiements: [{ id: 9, date: '2026-10-12', montant: 75000, mode_libelle: 'Espèces', numero: 'OP-2026-000001', annule: false }] }]);
    rendre(<MesFrais />);
    expect(await screen.findByText(/mensualité en retard/i)).toBeInTheDocument();
    expect(screen.getAllByText('En retard').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: /Reçu OP-2026-000001/ })).toBeInTheDocument();
  });

  it('résultats masqués : message', async () => {
    api.mesNotes.mockResolvedValue({ matricule: 'M', inscriptions: [{ inscription: 1, classe: 'L1 MIP — 2026-2027', annee: '2026-2027',
      statut: 'active', resultats_masques: true, message_resultats: 'Vos moyennes s’afficheront quand votre mensualité échue sera réglée.',
      semestres: [{ semestre: 'S1', deliberee: true, resultat: null, ues: [] }] }] });
    rendre(<MesNotes />);
    expect(await screen.findByText(/quand votre mensualité échue sera réglée/)).toBeInTheDocument();
    expect(screen.getByText('Délibéré — résultat masqué')).toBeInTheDocument();
    expect(screen.queryByText('En attente de délibération')).not.toBeInTheDocument();
  });

  it('reçu indisponible : message', async () => {
    api.mesFrais.mockResolvedValue([{ id: 1, annee_libelle: '2026-2027', classe_libelle: 'L1 MIP — 2026-2027', montant_du: 300,
      montant_paye: 150, reste: 150, en_retard: false, montant_en_retard: 0, statut: 'partiel', prochaine_echeance: null, echeances: [],
      paiements: [{ id: 9, date: '2026-10-12', montant: 150, mode_libelle: 'Espèces', numero: 'OP-2026-000001', annule: false }] }]);
    api.telechargerRecu.mockRejectedValue({ response: { status: 500 } });
    const user = userEvent.setup();
    rendre(<MesFrais />);
    await user.click(await screen.findByRole('button', { name: /Reçu OP-2026-000001/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/reçu/i);
  });
});
