import { describe, expect, it } from 'vitest';
import { CANVAS_MON_ESPACE, styleModule } from './modules';

describe('styleModule', () => {
  it('pose la couleur du module et, s’il y en a une, la toile', () => {
    expect(styleModule({ couleur: '1 2% 3%', canvas: '105 12% 93%' })).toEqual({ '--module': '1 2% 3%', '--canvas': '105 12% 93%' });
    expect(styleModule({ couleur: '1 2% 3%' })).toEqual({ '--module': '1 2% 3%' });
    expect(styleModule({})).toBeUndefined();
  });

  it('toile sauge de Mon espace', () => {
    expect(CANVAS_MON_ESPACE).toBe('105 12% 93%');
  });
});
