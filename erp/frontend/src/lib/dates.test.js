import { describe, expect, it } from 'vitest';
import { bornesSemaine, dateLongue, enIso, salutation } from './dates';

describe('dates', () => {
  it('salue selon l’heure', () => {
    expect(salutation(new Date(2026, 10, 21, 17, 59))).toBe('Bonjour');
    expect(salutation(new Date(2026, 10, 21, 18, 0))).toBe('Bonsoir');
  });

  it('écrit la date en toutes lettres, avec une capitale', () => {
    expect(dateLongue(new Date(2026, 10, 21))).toBe('Samedi 21 novembre 2026');
  });

  it('formate en ISO local', () => {
    expect(enIso(new Date(2026, 0, 5, 23, 30))).toBe('2026-01-05');
  });

  it('donne le lundi et le dimanche de la semaine', () => {
    expect(bornesSemaine(new Date(2026, 10, 19))).toEqual({ debut: '2026-11-16', fin: '2026-11-22' });
    expect(bornesSemaine(new Date(2026, 10, 22))).toEqual({ debut: '2026-11-16', fin: '2026-11-22' });
    expect(bornesSemaine(new Date(2026, 10, 16))).toEqual({ debut: '2026-11-16', fin: '2026-11-22' });
  });
});
