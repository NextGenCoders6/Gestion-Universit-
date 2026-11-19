import Pastille from '@/components/shared/Pastille';

const TON_ECHEANCE = { payee: 'vert', partielle: 'ambre', en_retard: 'rouge', a_venir: 'gris' };
const LIBELLE_ECHEANCE = { payee: 'Payée', partielle: 'Partielle', en_retard: 'En retard', a_venir: 'À venir' };

export function BadgeEcheance({ etat }) {
  return <Pastille ton={TON_ECHEANCE[etat]}>{LIBELLE_ECHEANCE[etat]}</Pastille>;
}

export function BadgeStatut({ libelle, ok, alerte }) {
  return <Pastille ton={ok ? 'vert' : alerte ? 'rouge' : 'gris'}>{libelle}</Pastille>;
}
