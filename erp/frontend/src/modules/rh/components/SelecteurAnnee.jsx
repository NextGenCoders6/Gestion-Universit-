/** Année des vacations affichées (l'année en cours par défaut). */
import { useQuery } from '@tanstack/react-query';
import Selecteur from '@/components/shared/Selecteur';

export default function SelecteurAnnee({ lister, valeur, onChange }) {
  const annees = useQuery({ queryKey: ['annees'], queryFn: lister, staleTime: 5 * 60 * 1000 });
  return (
    <Selecteur id="annee" label="Année" vide="Année en cours" valeur={valeur} className="max-w-xs" onChange={onChange}
      options={(annees.data ?? []).map((a) => ({ valeur: String(a.id), libelle: `${a.libelle}${a.en_cours ? ' (en cours)' : ''}` }))} />
  );
}
