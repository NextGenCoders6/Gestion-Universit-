import { afterEach, describe, expect, it, vi } from 'vitest';
import { moisCourant } from './format';

describe('moisCourant', () => {
  afterEach(() => vi.useRealTimers());
  it("suit l'heure locale, pas l'heure UTC", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 11, 1, 0, 30));   // 1er décembre, 00 h 30 heure locale
    expect(moisCourant()).toBe('2026-12');
  });
});
