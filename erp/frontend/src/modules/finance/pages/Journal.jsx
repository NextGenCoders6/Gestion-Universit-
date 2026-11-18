/** Journal des opérations : filtres, opérations manuelles (responsable), reçus, annulations. */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus, Printer } from '@/components/ui/icons';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import PageHeader from '@/components/shared/PageHeader';
import Selecteur from '@/components/shared/Selecteur';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import { MotifDialog } from '../components/Dialogues';
import { useEstResponsableFinance } from '../hooks';
import { dateFr, fcfa } from '../lib/format';

const CATEGORIES = [['frais', 'Frais de scolarité'], ['salaire', 'Salaires'], ['vacation', 'Vacations'], ['manuelle', 'Opérations manuelles'], ['annulation', 'Annulations']];

function OperationDialog({ onFermer, onCree }) {
  const form = useForm({ defaultValues: { libelle: '', sens: 'recette', montant: '', date: '' } });
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const [enCours, setEnCours] = useState(false);
  const soumettre = async (v) => {
    setEnCours(true);
    try {
      const montant = v.sens === 'depense' ? `-${String(v.montant).replace(/^-/, '')}` : v.montant;
      onCree(await api.creerOperation({ libelle: v.libelle, montant, date: v.date || null }));
      onFermer();
    } catch (e) { setErreurs(erreursServeur(e, ['libelle', 'montant', 'date'])); } finally { setEnCours(false); }
  };
  const erreur = (n) => erreurs.champs[n] ?? form.formState.errors[n]?.message;
  return (
    <FormModal open onClose={onFermer} title="Nouvelle opération" onConfirm={form.handleSubmit(soumettre)} isPending={enCours}>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="libelle" label="Libellé" requis register={form.register} erreur={erreur('libelle')} />
        <Champ nom="sens" label="Sens" type="select" requis register={form.register} options={[{ valeur: 'recette', libelle: 'Recette (+)' }, { valeur: 'depense', libelle: 'Dépense (−)' }]} />
        <Champ nom="montant" label="Montant (FCFA)" type="number" requis register={form.register} erreur={erreur('montant')} />
        <Champ nom="date" label="Date" type="date" register={form.register} erreur={erreur('date')} aide="Aujourd’hui si vide." />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}

export default function Journal() {
  const client = useQueryClient();
  const { toast } = useToast();
  const responsable = useEstResponsableFinance();
  const [filtre, setFiltre] = useState({ debut: '', fin: '', categorie: '', q: '', page: 1 });
  const [dialogue, setDialogue] = useState(null);
  const requete = Object.fromEntries(Object.entries(filtre).filter(([, v]) => v));
  const liste = useQuery({ queryKey: ['finance', 'journal', requete], queryFn: () => api.listerOperations(requete), placeholderData: keepPreviousData });
  const changer = (c, v) => setFiltre((f) => ({ ...f, [c]: v, page: 1 }));
  const recu = async (o) => {
    try { await api.telecharger(`/finance/operations/${o.id}/recu.pdf`, `recu-${o.numero}.pdf`); } catch (e) {
      toast({ title: 'Reçu indisponible', description: erreursServeur(e).global, variant: 'destructive' });
    }
  };
  const operations = liste.data?.results ?? [];
  const pages = Math.max(1, Math.ceil((liste.data?.count ?? 0) / 20));
  return (
    <div className="space-y-4">
      <PageHeader titre="Journal des opérations" description="Chaque paiement y écrit sa ligne ; une erreur se corrige par une annulation, jamais par une suppression.">
        {responsable && <Button onClick={() => setDialogue('nouvelle')}><Plus /> Nouvelle opération</Button>}
      </PageHeader>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-1.5"><Label htmlFor="debut">Du</Label><Input id="debut" type="date" value={filtre.debut} onChange={(e) => changer('debut', e.target.value)} /></div>
        <div className="space-y-1.5"><Label htmlFor="fin">Au</Label><Input id="fin" type="date" value={filtre.fin} onChange={(e) => changer('fin', e.target.value)} /></div>
        <Selecteur id="categorie" label="Catégorie" vide="Toutes" valeur={filtre.categorie} onChange={(v) => changer('categorie', v)}
          options={CATEGORIES.map(([valeur, libelle]) => ({ valeur, libelle }))} />
        <div className="space-y-1.5"><Label htmlFor="q">Rechercher</Label><Input id="q" value={filtre.q} onChange={(e) => changer('q', e.target.value)} placeholder="Libellé ou numéro" /></div>
      </div>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs uppercase text-muted-foreground"><tr>
            <th className="px-3 py-2 text-left">N°</th><th className="px-3 py-2 text-left">Date</th><th className="px-3 py-2 text-left">Libellé</th><th className="px-3 py-2 text-right">Montant</th><th className="px-2 py-2" />
          </tr></thead>
          <tbody>
            {operations.length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">Aucune opération.</td></tr>}
            {operations.map((o) => (
              <tr key={o.id} className={`border-t border-border ${o.est_annulee ? 'text-muted-foreground line-through' : ''}`}>
                <td className="px-3 py-1.5 font-mono text-xs">{o.numero}</td>
                <td className="px-3 py-1.5">{dateFr(o.date)}</td>
                <td className="px-3 py-1.5">{o.libelle}<div className="text-xs text-muted-foreground">{o.categorie_libelle}</div></td>
                <td className={`px-3 py-1.5 text-right font-semibold ${o.montant >= 0 ? 'text-primary' : 'text-destructive'}`}>{o.montant >= 0 ? '+' : '−'}{fcfa(Math.abs(o.montant))}</td>
                <td className="px-2 py-1.5 text-right whitespace-nowrap">
                  <Button size="sm" variant="ghost" onClick={() => recu(o)}><Printer /> Reçu</Button>
                  {responsable && o.categorie === 'manuelle' && !o.est_annulee && <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setDialogue({ annuler: o })}>Annuler</Button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <Button variant="outline" size="sm" disabled={filtre.page <= 1} onClick={() => setFiltre((f) => ({ ...f, page: f.page - 1 }))}>Précédente</Button>
          <span>Page {filtre.page} / {pages}</span>
          <Button variant="outline" size="sm" disabled={filtre.page >= pages} onClick={() => setFiltre((f) => ({ ...f, page: f.page + 1 }))}>Suivante</Button>
        </div>
      )}
      {dialogue === 'nouvelle' && <OperationDialog onFermer={() => setDialogue(null)}
        onCree={(o) => { client.invalidateQueries({ queryKey: ['finance'] }); toast({ title: 'Opération enregistrée', description: o.numero }); }} />}
      {dialogue?.annuler && <MotifDialog titre="Annuler cette opération ?" libelleBouton="Annuler l’opération" description={`${dialogue.annuler.numero} — ${dialogue.annuler.libelle}`}
        onFermer={() => setDialogue(null)}
        envoyer={async (motif) => { await api.annulerOperation(dialogue.annuler.id, motif); client.invalidateQueries({ queryKey: ['finance'] }); toast({ title: 'Opération annulée' }); }} />}
    </div>
  );
}
