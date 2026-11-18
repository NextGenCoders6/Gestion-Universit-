import { describe, expect, it } from 'vitest';
import { erreursServeur } from './erreurs';

const erreur = (data, status = 400) => ({ response: { status, data } });

describe('erreursServeur', () => {
  it('range non_field_errors en message général', () => {
    expect(erreursServeur(erreur({ non_field_errors: ['Cette classe existe déjà pour cette année.'] })))
      .toEqual({ champs: {}, global: 'Cette classe existe déjà pour cette année.' });
  });

  it('envoie en message général une clé qui ne correspond à aucun champ du formulaire', () => {
    const r = erreursServeur(erreur({ __all__: ['Erreur générale.'], code: ['X'], nom: ['Trop court.'] }), ['nom', 'code']);
    expect(r).toEqual({ champs: { nom: 'Trop court.', code: 'X' }, global: 'Erreur générale.' });
  });

  it('sans liste de champs, toutes les clés restent des erreurs de champ', () => {
    expect(erreursServeur(erreur({ filiere: ['Invalide.'] })).champs).toEqual({ filiere: 'Invalide.' });
  });
});

describe('messageErreur', () => {
  it('message général, sinon le premier message de champ', async () => {
    const { messageErreur } = await import('./erreurs');
    expect(messageErreur({ response: { status: 400, data: { detail: 'Refusé.' } } })).toBe('Refusé.');
    expect(messageErreur({ response: { status: 400, data: { echeances: ['La somme doit être égale au montant dû.'] } } }))
      .toBe('La somme doit être égale au montant dû.');
  });
});
