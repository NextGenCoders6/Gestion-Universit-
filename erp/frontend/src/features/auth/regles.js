// Règles de saisie communes aux pages publiques du compte (react-hook-form).
export const AIDE_MOT_DE_PASSE = 'Au moins 8 caractères, pas uniquement des chiffres.';
export const REQUIS = { required: 'Ce champ est obligatoire.' };
export const confirmationIdentique = (v, tout) => v === tout.password || 'Les deux mots de passe ne correspondent pas.';
