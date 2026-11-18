import { useState } from 'react';
import { useWatch } from 'react-hook-form';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Pencil, Plus, Trash2 } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { confirmer } from '@/lib/confirmer';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import Formulaire from '../Formulaire';
import { STATUTS_BUS, useEstResponsableLogistique } from '../hooks';

const CHAMPS = [
  { nom: 'numero', label: 'Numéro', requis: true },
  { nom: 'plaque', label: 'Plaque', requis: true },
  { nom: 'capacite', label: 'Capacité (places)', type: 'number', requis: true },
];

function AvertissementStatut({ form, bus }) {
  const statut = useWatch({ control: form.control, name: 'statut' });
  if (!bus.affectation_active || !statut || statut === 'actif') return null;
  return <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-900/20 dark:text-amber-100">
    L’affectation en cours ({bus.affectation_active.chauffeur}, {bus.affectation_active.trajet}) sera terminée aujourd’hui.</p>;
}

export default function Bus() {
  const client = useQueryClient();
  const { toast } = useToast();
  const responsable = useEstResponsableLogistique();
  const bus = useQuery({ queryKey: ['logistique', 'bus'], queryFn: api.listerBus });
  const [dialogue, setDialogue] = useState(null);
  const rafraichir = () => client.invalidateQueries({ queryKey: ['logistique'] });
  const libelle = (s) => STATUTS_BUS.find((x) => x.valeur === s)?.libelle ?? s;
  return (
    <div className="space-y-4">
      <PageHeader titre="Bus" description="Parc de bus, statut et affectation en cours.">
        {responsable && <Button onClick={() => setDialogue('nouveau')}><Plus /> Nouveau bus</Button>}
      </PageHeader>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {(bus.data ?? []).map((b) => (
          <article key={b.id} className="space-y-2 rounded-lg border border-border bg-card p-4">
            <header className="flex items-start justify-between gap-2">
              <div><h3 className="font-semibold">Bus {b.numero}</h3><p className="text-xs text-muted-foreground">{b.plaque} · {b.capacite} places</p></div>
              <Badge variant={b.statut === 'actif' ? 'secondary' : 'outline'}>{libelle(b.statut)}</Badge>
            </header>
            <p className="text-sm">{b.affectation_active ? <>{b.affectation_active.chauffeur} · {b.affectation_active.trajet}</> : <span className="text-muted-foreground">Aucune affectation en cours</span>}</p>
            {responsable && (
              <div className="flex gap-1">
                <Button size="sm" variant="outline" aria-label={`Statut du bus ${b.numero}`} onClick={() => setDialogue({ statut: b })}>Statut</Button>
                <Button size="icon-sm" variant="ghost" aria-label={`Modifier le bus ${b.numero}`} onClick={() => setDialogue({ modifier: b })}><Pencil /></Button>
                <Button size="icon-sm" variant="ghost" className="text-destructive" aria-label={`Supprimer le bus ${b.numero}`} onClick={async () => {
                  if (!(await confirmer({ titre: `Supprimer le bus ${b.numero} ?`, libelleConfirmer: 'Supprimer', destructif: true }))) return;
                  try { await api.supprimerBus(b.id); rafraichir(); } catch (e) { toast({ title: 'Suppression impossible', description: erreursServeur(e).global, variant: 'destructive' }); }
                }}><Trash2 /></Button>
              </div>
            )}
          </article>
        ))}
      </div>
      {bus.data?.length === 0 && <p className="text-sm text-muted-foreground">Aucun bus.</p>}
      {dialogue === 'nouveau' && <Formulaire titre="Nouveau bus" champs={CHAMPS} onFermer={() => setDialogue(null)}
        envoyer={async (v) => { await api.creerBus(v); rafraichir(); toast({ title: 'Bus ajouté' }); }} />}
      {dialogue?.modifier && <Formulaire titre={`Bus ${dialogue.modifier.numero}`} champs={CHAMPS} valeurs={dialogue.modifier} onFermer={() => setDialogue(null)}
        envoyer={async (v) => { await api.modifierBus(dialogue.modifier.id, v); rafraichir(); toast({ title: 'Bus modifié' }); }} />}
      {dialogue?.statut && <Formulaire titre={`Statut du bus ${dialogue.statut.numero}`} valeurs={{ statut: dialogue.statut.statut }}
        champs={[{ nom: 'statut', label: 'Statut', type: 'select', requis: true, options: STATUTS_BUS }]} onFermer={() => setDialogue(null)}
        enfants={(form) => <AvertissementStatut form={form} bus={dialogue.statut} />}
        envoyer={async (v) => {
          const r = await api.changerStatut(dialogue.statut.id, v.statut);
          rafraichir();
          toast({ title: 'Statut mis à jour', description: r.affectations_terminees ? `${r.affectations_terminees} affectation terminée.` : undefined });
        }} />}
    </div>
  );
}
