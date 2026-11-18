import { describe, expect, it } from 'vitest';
import { valeursInitiales, versApi } from './formulaire';

const CHAMPS = [
  { nom: 'nom' },
  { nom: 'date_naissance', type: 'date' },
  { nom: 'email', type: 'email' },
  { nom: 'faculte', source: { ressource: 'facultes' } },
  { nom: 'credits', type: 'number' },
  { nom: 'actif', type: 'checkbox' },
];

describe('conversion des formulaires', () => {
  it('envoie null pour une date, un e-mail, une référence ou un nombre vides', () => {
    expect(versApi(CHAMPS, { nom: 'A', date_naissance: '', email: '', faculte: '', credits: '', actif: false }))
      .toEqual({ nom: 'A', date_naissance: null, email: null, faculte: null, credits: null, actif: false });
  });

  it('convertit références et nombres', () => {
    expect(versApi(CHAMPS, { nom: 'A', date_naissance: '2000-01-02', email: 'a@b.cg', faculte: '3', credits: '4', actif: true }))
      .toEqual({ nom: 'A', date_naissance: '2000-01-02', email: 'a@b.cg', faculte: 3, credits: 4, actif: true });
  });

  it('valeursInitiales remplace null par une chaîne vide', () => {
    expect(valeursInitiales(CHAMPS, { nom: 'A', date_naissance: null, faculte: 2, actif: 1 }))
      .toEqual({ nom: 'A', date_naissance: '', email: '', faculte: '2', credits: '', actif: true });
  });
});
