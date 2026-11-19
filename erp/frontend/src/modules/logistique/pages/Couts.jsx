import { useQuery } from '@tanstack/react-query';
import { BarresRepartition as Barres } from '@/components/shared/Graphiques';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';
import { TYPES_DEPENSE } from '../hooks';

const fcfa = (v) => `${Number(v ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} FCFA`;

export default function Couts() {
  const c = useQuery({ queryKey: ['logistique', 'couts'], queryFn: () => api.couts() }).data;
  return (
    <div className="space-y-4">
      <PageHeader titre="Coûts" description="Dépenses de transport enregistrées par la Finance (lecture seule)." />
      {!c ? <p className="text-sm text-muted-foreground">Chargement…</p> : (
        <>
          <div className="carte p-5"><p className="text-sm font-medium text-muted-foreground">Total des dépenses de transport</p><p className="chiffres mt-1 text-[28px] font-semibold tracking-tight">{fcfa(c.total)}</p></div>
          <div className="grid gap-4 lg:grid-cols-3">
            <section className="carte p-5"><h2 className="mb-4 font-semibold tracking-tight">Par bus</h2>
              <Barres formater={fcfa} lignes={c.par_bus.map((b) => ({ libelle: `Bus ${b.numero}`, valeur: b.total }))} /></section>
            <section className="carte p-5"><h2 className="mb-4 font-semibold tracking-tight">Par type</h2>
              <Barres formater={fcfa} lignes={Object.entries(c.par_type).map(([t, v]) => ({ libelle: TYPES_DEPENSE[t] ?? t, valeur: v }))} /></section>
            <section className="carte p-5"><h2 className="mb-4 font-semibold tracking-tight">Par mois</h2>
              <Barres formater={fcfa} lignes={Object.entries(c.par_mois).map(([m, v]) => ({ libelle: m, valeur: v }))} /></section>
          </div>
        </>
      )}
    </div>
  );
}
