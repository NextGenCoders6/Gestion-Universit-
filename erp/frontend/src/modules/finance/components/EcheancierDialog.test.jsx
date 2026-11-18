import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import EcheancierDialog from './EcheancierDialog';

describe('Adaptation de l’échéancier', () => {
  it('affiche le message précis du serveur', async () => {
    const envoyer = vi.fn().mockRejectedValue({ response: { status: 400, data: { echeances: ['Les dates limites doivent être croissantes.'] } } });
    const user = userEvent.setup();
    render(<EcheancierDialog dossier={{ montant_du: 300, echeances: [
      { mois: '2026-10', date_limite: '2026-11-05', montant: 150 }, { mois: '2026-11', date_limite: '2026-12-05', montant: 150 }] }}
      envoyer={envoyer} onFermer={() => {}} />);
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }));
    expect(await screen.findByText('Les dates limites doivent être croissantes.')).toBeInTheDocument();
  });
});
