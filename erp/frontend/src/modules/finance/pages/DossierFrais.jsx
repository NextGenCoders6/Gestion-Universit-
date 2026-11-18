/** Dossier de frais : échéancier, paiements, encaissement, reçus ; ajustement et annulations (responsable). */
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Printer } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import { BadgeEcheance, BadgeStatut } from '../components/Badges';
import { MontantDialog, MotifDialog, PaiementDialog } from '../components/Dialogues';
import EcheancierDialog from '../components/EcheancierDialog';
import { useEstResponsableFinance } from '../hooks';
import { dateFr, fcfa, STATUTS_FRAIS } from '../lib/format';

export default function DossierFrais() {
  const { id } = useParams();
  const client = useQueryClient();
  const { toast } = useToast();
  const responsable = useEstResponsableFinance();
  const dossier = useQuery({ queryKey: ['finance', 'dossier', id], queryFn: () => api.dossierFrais(id) });
  const [dialogue, setDialogue] = useState(null);
  const rafraichir = () => client.invalidateQueries({ queryKey: ['finance'] });
  const recu = async (p) => {
    try { await api.telecharger(`/finance/paiements/${p.id}/recu.pdf`, `recu-${p.numero}.pdf`); } catch (e) {
      toast({ title: 'Reçu indisponible', description: erreursServeur(e).global, variant: 'destructive' });
    }
  };
  if (dossier.isLoading) return <p className="text-sm text-muted-foreground">Chargement…</p>;
  if (dossier.isError) return <p className="text-sm text-destructive">{erreursServeur(dossier.error).global}</p>;
  const d = dossier.data;
  return (
    <div className="space-y-4">
      <Link to=".." relative="path" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="size-4" /> Tous les dossiers</Link>
      <PageHeader titre={d.nom_complet} description={`${d.matricule} · ${d.classe_libelle}`}>
        <Button onClick={() => setDialogue('paiement')} disabled={d.reste <= 0}>Encaisser un paiement</Button>
        {responsable && <Button variant="outline" onClick={() => setDialogue('montant')}>Ajuster le montant</Button>}
        {responsable && d.echeances.length > 0 && <Button variant="outline" onClick={() => setDialogue('echeancier')}>Adapter l’échéancier</Button>}
      </PageHeader>
      <div className="grid gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-border bg-card p-3"><p className="text-xs text-muted-foreground">Montant dû</p><p className="font-bold">{fcfa(d.montant_du)}{d.montant_ajuste && <span className="ml-1 text-xs font-normal text-muted-foreground">(ajusté)</span>}</p></div>
        <div className="rounded-lg border border-border bg-card p-3"><p className="text-xs text-muted-foreground">Payé</p><p className="font-bold">{fcfa(d.montant_paye)}</p></div>
        <div className="rounded-lg border border-border bg-card p-3"><p className="text-xs text-muted-foreground">Reste</p><p className="font-bold">{fcfa(d.reste)}</p>{d.trop_percu > 0 && <p className="text-xs text-amber-700">Trop-perçu : {fcfa(d.trop_percu)}</p>}</div>
        <div className="rounded-lg border border-border bg-card p-3"><p className="text-xs text-muted-foreground">Situation</p>
          {d.sans_tarif ? <BadgeStatut libelle="Sans tarif" alerte /> : d.en_retard ? <BadgeStatut libelle={`En retard : ${fcfa(d.montant_en_retard)}`} alerte /> : <BadgeStatut libelle={STATUTS_FRAIS[d.statut]} ok={d.statut === 'paye'} />}</div>
      </div>
      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-2 font-semibold">Échéancier{d.echeancier_adapte && <span className="ml-2 text-xs font-normal text-muted-foreground">adapté</span>}</h2>
        {d.echeances.length === 0 ? <p className="text-sm text-muted-foreground">Pas d’échéancier (aucun montant dû).</p> : (
          <table className="w-full text-sm">
            <thead className="text-xs text-muted-foreground"><tr><th className="py-1 text-left">Mois couvert</th><th>À payer avant le</th><th>Mensualité</th><th>Payé</th><th>État</th></tr></thead>
            <tbody>{d.echeances.map((e) => (
              <tr key={e.numero} aria-label={e.mois} className="border-t border-border">
                <td className="py-1.5">{e.mois}</td><td className="text-center">{dateFr(e.date_limite)}</td>
                <td className="text-center">{fcfa(e.montant)}</td><td className="text-center">{fcfa(e.paye)}</td>
                <td className="text-center"><BadgeEcheance etat={e.etat} /></td>
              </tr>))}</tbody>
          </table>
        )}
      </section>
      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-2 font-semibold">Paiements</h2>
        {d.paiements.length === 0 && <p className="text-sm text-muted-foreground">Aucun paiement.</p>}
        <ul className="space-y-1">{d.paiements.map((p) => (
          <li key={p.id} className={`flex flex-wrap items-center justify-between gap-2 rounded-md px-3 py-2 text-sm ${p.annule ? 'bg-muted/30 text-muted-foreground line-through' : 'bg-muted/40'}`}>
            <span>{dateFr(p.date)} · {fcfa(p.montant)} · {p.mode_libelle}{p.reference && ` · ${p.reference}`} · {p.numero}{p.annule && ` — annulé : ${p.motif_annulation}`}</span>
            <span className="flex gap-1">
              <Button size="sm" variant="ghost" onClick={() => recu(p)}><Printer /> Reçu</Button>
              {responsable && !p.annule && <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setDialogue({ annuler: p })}>Annuler</Button>}
            </span>
          </li>))}</ul>
      </section>
      {dialogue === 'paiement' && (
        <PaiementDialog titre={`Encaisser — ${d.nom_complet}`} reste={d.reste} onFermer={() => setDialogue(null)}
          envoyer={async (v) => {
            const r = await api.encaisser(d.id, { montant: v.montant, mode: v.mode, date: v.date || null, reference: v.reference });
            rafraichir();
            toast({ title: 'Paiement enregistré', description: `${fcfa(r.paiement.montant)} · ${r.paiement.numero}` });
          }} />
      )}
      {dialogue === 'montant' && (
        <MontantDialog titre="Ajuster le montant dû" valeur={d.montant_du} onFermer={() => setDialogue(null)}
          description="Le tarif ne changera plus ce dossier. L’échéancier est redistribué sur les mêmes mois."
          envoyer={async (m) => { await api.ajusterFrais(d.id, m); rafraichir(); toast({ title: 'Montant ajusté' }); }} />
      )}
      {dialogue === 'echeancier' && (
        <EcheancierDialog dossier={d} onFermer={() => setDialogue(null)}
          envoyer={async (l) => { await api.adapterEcheancier(d.id, l); rafraichir(); toast({ title: 'Échéancier adapté' }); }} />
      )}
      {dialogue?.annuler && (
        <MotifDialog titre="Annuler ce paiement ?" description={`${fcfa(dialogue.annuler.montant)} du ${dateFr(dialogue.annuler.date)} — une écriture inverse sera ajoutée au journal.`}
          onFermer={() => setDialogue(null)}
          envoyer={async (motif) => { await api.annulerPaiement(dialogue.annuler.id, motif); rafraichir(); toast({ title: 'Paiement annulé' }); }} />
      )}
    </div>
  );
}
