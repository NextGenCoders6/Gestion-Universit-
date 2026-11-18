import { useQuery } from '@tanstack/react-query';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';
import { TYPES_DEPENSE } from '../hooks';

const fcfa = (v) => `${Number(v ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} FCFA`;

function Barres({ lignes }) {
  const max = Math.max(1, ...lignes.map((l) => l.valeur));
  return (
    <ul className="space-y-1.5">
      {lignes.map((l) => (
        <li key={l.libelle} className="text-sm">
          <div className="flex justify-between"><span>{l.libelle}</span><span className="font-medium">{fcfa(l.valeur)}</span></div>
          <div className="h-2 rounded bg-muted"><div className="h-2 rounded bg-primary" style={{ width: `${(l.valeur / max) * 100}%` }} /></div>
        </li>
      ))}
    </ul>
  );
}

export default function Couts() {
  const c = useQuery({ queryKey: ['logistique', 'couts'], queryFn: () => api.couts() }).data;
  return (
    <div className="space-y-4">
      <PageHeader titre="Coûts" description="Dépenses de transport enregistrées par la Finance (lecture seule)." />
      {!c ? <p className="text-sm text-muted-foreground">Chargement…</p> : (
        <>
          <div className="rounded-lg border border-border bg-card p-4"><p className="text-xs uppercase text-muted-foreground">Total</p><p className="text-2xl font-bold">{fcfa(c.total)}</p></div>
          <div className="grid gap-4 lg:grid-cols-3">
            <section className="rounded-lg border border-border bg-card p-4"><h2 className="mb-2 font-semibold">Par bus</h2>
              <Barres lignes={c.par_bus.map((b) => ({ libelle: `Bus ${b.numero}`, valeur: b.total }))} /></section>
            <section className="rounded-lg border border-border bg-card p-4"><h2 className="mb-2 font-semibold">Par type</h2>
              <Barres lignes={Object.entries(c.par_type).map(([t, v]) => ({ libelle: TYPES_DEPENSE[t] ?? t, valeur: v }))} /></section>
            <section className="rounded-lg border border-border bg-card p-4"><h2 className="mb-2 font-semibold">Par mois</h2>
              <Barres lignes={Object.entries(c.par_mois).map(([m, v]) => ({ libelle: m, valeur: v }))} /></section>
          </div>
        </>
      )}
    </div>
  );
}
