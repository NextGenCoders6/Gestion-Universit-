/** Situation des frais de l'étudiant : échéancier, prochaine échéance, retards, paiements et reçus. */
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Printer } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import { BadgeEcheance } from '@/modules/finance/components/Badges';
import { dateFr, fcfa } from '@/modules/finance/lib/format';
import * as api from '../api';

function Dossier({ d }) {
  const p = d.prochaine_echeance;
  return (
    <section className="space-y-3 rounded-lg border border-border bg-card p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">{d.classe_libelle}</h2>
        <p className="text-sm">{fcfa(d.montant_paye)} payés sur {fcfa(d.montant_du)} · reste {fcfa(d.reste)}</p>
      </header>
      {d.en_retard ? (
        <p role="alert" className="flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertTriangle className="size-4" /> Une mensualité en retard : {fcfa(d.montant_en_retard)} à régler au plus vite.
        </p>
      ) : p ? (
        <p className="rounded-md bg-muted/40 px-3 py-2 text-sm">Prochaine échéance : <strong>{fcfa(p.montant - p.paye)}</strong> avant le <strong>{dateFr(p.date_limite)}</strong> (mois de {p.mois}).</p>
      ) : d.montant_du > 0 && <p className="rounded-md bg-primary/10 px-3 py-2 text-sm text-primary">Frais de l’année soldés.</p>}
      {d.echeances.length > 0 && (
        <table className="w-full text-sm">
          <thead className="text-xs text-muted-foreground"><tr><th className="py-1 text-left">Mois</th><th>Avant le</th><th>Mensualité</th><th>Payé</th><th>État</th></tr></thead>
          <tbody>{d.echeances.map((e) => (
            <tr key={e.numero} className="border-t border-border">
              <td className="py-1.5">{e.mois}</td><td className="text-center">{dateFr(e.date_limite)}</td>
              <td className="text-center">{fcfa(e.montant)}</td><td className="text-center">{fcfa(e.paye)}</td>
              <td className="text-center"><BadgeEcheance etat={e.etat} /></td>
            </tr>))}</tbody>
        </table>
      )}
      <div>
        <h3 className="mb-1 text-sm font-medium">Paiements</h3>
        {d.paiements.length === 0 && <p className="text-sm text-muted-foreground">Aucun paiement enregistré.</p>}
        <ul className="space-y-1">{d.paiements.map((x) => (
          <li key={x.id} className="flex items-center justify-between gap-2 rounded-md bg-muted/40 px-3 py-1.5 text-sm">
            <span>{dateFr(x.date)} · {fcfa(x.montant)} · {x.mode_libelle}</span>
            <Button size="sm" variant="ghost" aria-label={`Reçu ${x.numero}`} onClick={() => api.telechargerRecu(x)}><Printer /> Reçu</Button>
          </li>))}</ul>
      </div>
    </section>
  );
}

export default function MesFrais() {
  const frais = useQuery({ queryKey: ['moi', 'frais'], queryFn: api.mesFrais });
  return (
    <div className="space-y-4">
      <PageHeader titre="Mes frais" description="Frais de scolarité payables par mensualités : chaque mois écoulé se règle avant sa date limite." />
      {frais.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
      {frais.data?.length === 0 && <p className="text-sm text-muted-foreground">Aucun dossier de frais.</p>}
      {(frais.data ?? []).map((d) => <Dossier key={d.id} d={d} />)}
    </div>
  );
}
