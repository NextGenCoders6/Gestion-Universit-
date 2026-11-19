/** Dépenses de transport : saisie (responsable), annulation, reçus. La Logistique les lit dans « Coûts ». */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Plus, Printer } from '@/components/ui/icons';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import { MotifDialog } from '../components/Dialogues';
import { useEstResponsableFinance } from '../hooks';
import { dateFr, fcfa } from '../lib/format';

const TYPES = [{ valeur: 'carburant', libelle: 'Carburant' }, { valeur: 'entretien', libelle: 'Entretien' }, { valeur: 'reparation', libelle: 'Réparation' }];

function DepenseDialog({ onFermer, onCree }) {
  const bus = useQuery({ queryKey: ['finance', 'bus'], queryFn: api.listerBusFinance });
  const form = useForm({ defaultValues: { bus: '', type: '', montant: '', date: '', description: '' } });
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const [enCours, setEnCours] = useState(false);
  const soumettre = async (v) => {
    setEnCours(true);
    try { onCree(await api.creerDepense({ ...v, bus: Number(v.bus), date: v.date || null })); onFermer(); }
    catch (e) { setErreurs(erreursServeur(e, ['bus', 'type', 'montant', 'date', 'description'])); } finally { setEnCours(false); }
  };
  const erreur = (n) => erreurs.champs[n] ?? form.formState.errors[n]?.message;
  return (
    <FormModal open onClose={onFermer} title="Nouvelle dépense de transport" onConfirm={form.handleSubmit(soumettre)} isPending={enCours}>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="bus" label="Bus" type="select" requis register={form.register} erreur={erreur('bus')}
          options={(bus.data ?? []).map((b) => ({ valeur: String(b.id), libelle: `Bus ${b.numero} (${b.plaque})` }))} />
        <Champ nom="type" label="Type" type="select" requis register={form.register} erreur={erreur('type')} options={TYPES} />
        <Champ nom="montant" label="Montant (FCFA)" type="number" requis register={form.register} erreur={erreur('montant')} />
        <Champ nom="date" label="Date" type="date" register={form.register} erreur={erreur('date')} aide="Aujourd’hui si vide." />
        <Champ nom="description" label="Description" register={form.register} erreur={erreur('description')} />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}

export default function Transports() {
  const client = useQueryClient();
  const { toast } = useToast();
  const responsable = useEstResponsableFinance();
  const [dialogue, setDialogue] = useState(null);
  const liste = useQuery({ queryKey: ['finance', 'transports'], queryFn: () => api.listerTransports({ page_size: 200 }) });
  const rafraichir = () => client.invalidateQueries({ queryKey: ['finance'] });
  const recu = async (d) => {
    try { await api.telecharger(`/finance/transports/${d.id}/recu.pdf`, `recu-${d.numero}.pdf`); } catch (e) {
      toast({ title: 'Reçu indisponible', description: erreursServeur(e).global, variant: 'destructive' });
    }
  };
  const lignes = liste.data?.results ?? [];
  return (
    <div className="space-y-4">
      <PageHeader titre="Transports" description="Carburant, entretien et réparations des bus ; chaque dépense passe au journal.">
        {responsable && <Button onClick={() => setDialogue('nouvelle')}><Plus /> Nouvelle dépense</Button>}
      </PageHeader>
      <div className="carte overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-[11px] uppercase tracking-wider text-muted-foreground"><tr>
            <th className="px-3 py-2 text-left">Date</th><th className="px-3 py-2 text-left">Bus</th><th className="px-3 py-2 text-left">Dépense</th><th className="px-3 py-2 text-right">Montant</th><th className="px-2 py-2" />
          </tr></thead>
          <tbody>
            {lignes.length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">Aucune dépense.</td></tr>}
            {lignes.map((d) => (
              <tr key={d.id} className={`border-t border-border ${d.annule ? 'text-muted-foreground line-through' : ''}`}>
                <td className="px-3 py-1.5">{dateFr(d.date)}</td><td className="px-3 py-1.5">Bus {d.bus_numero}</td>
                <td className="px-3 py-1.5">{d.type_libelle}{d.description && ` — ${d.description}`}<div className="text-xs text-muted-foreground">{d.numero}</div></td>
                <td className="px-3 py-1.5 text-right font-semibold">{fcfa(d.montant)}</td>
                <td className="px-2 py-1.5 text-right whitespace-nowrap">
                  <Button size="sm" variant="ghost" onClick={() => recu(d)}><Printer /> Reçu</Button>
                  {responsable && !d.annule && <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setDialogue({ annuler: d })}>Annuler</Button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {dialogue === 'nouvelle' && <DepenseDialog onFermer={() => setDialogue(null)} onCree={(d) => { rafraichir(); toast({ title: 'Dépense enregistrée', description: d.numero }); }} />}
      {dialogue?.annuler && <MotifDialog titre="Annuler cette dépense ?" libelleBouton="Annuler la dépense" description={`${fcfa(dialogue.annuler.montant)} — Bus ${dialogue.annuler.bus_numero}`}
        onFermer={() => setDialogue(null)}
        envoyer={async (motif) => { await api.annulerDepense(dialogue.annuler.id, motif); rafraichir(); toast({ title: 'Dépense annulée' }); }} />}
    </div>
  );
}
