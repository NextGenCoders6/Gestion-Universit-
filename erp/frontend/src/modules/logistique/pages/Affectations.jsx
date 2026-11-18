import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Plus } from '@/components/ui/icons';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import PageHeader from '@/components/shared/PageHeader';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur, messageErreur } from '@/lib/erreurs';
import * as api from '../api';
import Formulaire from '../Formulaire';
import { useEstResponsableLogistique } from '../hooks';

const dateFr = (d) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString('fr-FR') : '—');
const aujourdhui = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); };

/** Les chauffeurs proposés sont ceux disponibles à la date de début choisie. */
function NouvelleAffectation({ onFermer, onCree }) {
  const form = useForm({ defaultValues: { bus: '', chauffeur: '', trajet: '', date_debut: aujourdhui() } });
  const jour = useWatch({ control: form.control, name: 'date_debut' });
  const bus = useQuery({ queryKey: ['logistique', 'bus'], queryFn: api.listerBus });
  const trajets = useQuery({ queryKey: ['logistique', 'trajets'], queryFn: api.listerTrajets });
  const chauffeurs = useQuery({ queryKey: ['logistique', 'chauffeurs', jour], queryFn: () => api.chauffeursDisponibles(jour), enabled: Boolean(jour) });
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const [enCours, setEnCours] = useState(false);
  const soumettre = async (v) => {
    setEnCours(true);
    try {
      await api.creerAffectation({ bus: Number(v.bus), chauffeur: Number(v.chauffeur), trajet: Number(v.trajet), date_debut: v.date_debut });
      onCree(); onFermer();
    } catch (e) { setErreurs(erreursServeur(e, ['bus', 'chauffeur', 'trajet', 'date_debut'])); } finally { setEnCours(false); }
  };
  const erreur = (n) => erreurs.champs[n] ?? form.formState.errors[n]?.message;
  const r = form.register;
  return (
    <FormModal open onClose={onFermer} title="Nouvelle affectation" onConfirm={form.handleSubmit(soumettre)} isPending={enCours}>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="date_debut" label="À partir du" type="date" requis register={r} erreur={erreur('date_debut')} />
        <Champ nom="bus" label="Bus" type="select" requis register={r} erreur={erreur('bus')}
          options={(bus.data ?? []).filter((b) => b.statut === 'actif').map((b) => ({ valeur: String(b.id), libelle: `Bus ${b.numero} (${b.plaque})${b.affectation_active ? ' — déjà affecté' : ''}` }))} />
        <Champ nom="chauffeur" label="Chauffeur" type="select" requis register={r} erreur={erreur('chauffeur')}
          aide="Chauffeurs sous contrat et sans affectation à cette date."
          options={(chauffeurs.data ?? []).map((c) => ({ valeur: String(c.id), libelle: c.nom_complet }))} />
        <Champ nom="trajet" label="Trajet" type="select" requis register={r} erreur={erreur('trajet')}
          options={(trajets.data ?? []).map((t) => ({ valeur: String(t.id), libelle: t.nom }))} />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}

export default function Affectations() {
  const client = useQueryClient();
  const { toast } = useToast();
  const responsable = useEstResponsableLogistique();
  const [onglet, setOnglet] = useState('actives');
  const [dialogue, setDialogue] = useState(null);
  const liste = useQuery({ queryKey: ['logistique', 'affectations', onglet],
    queryFn: () => api.listerAffectations(onglet === 'actives' ? { actives: 'true', page_size: 200 } : { page_size: 200 }) });
  const rafraichir = () => client.invalidateQueries({ queryKey: ['logistique'] });
  const lignes = liste.data?.results ?? [];
  return (
    <div className="space-y-4">
      <PageHeader titre="Affectations" description="Un chauffeur, un bus, un trajet : une seule affectation active par bus et par chauffeur.">
        {responsable && <Button onClick={() => setDialogue('nouvelle')}><Plus /> Nouvelle affectation</Button>}
      </PageHeader>
      <Tabs value={onglet} onValueChange={setOnglet}><TabsList><TabsTrigger value="actives">En cours</TabsTrigger><TabsTrigger value="toutes">Toutes</TabsTrigger></TabsList></Tabs>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs uppercase text-muted-foreground"><tr>
            <th className="px-3 py-2 text-left">Bus</th><th className="px-3 py-2 text-left">Chauffeur</th><th className="px-3 py-2 text-left">Trajet</th><th className="px-3 py-2">Période</th><th className="px-2 py-2" />
          </tr></thead>
          <tbody>
            {lignes.length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">Aucune affectation.</td></tr>}
            {lignes.map((a) => (
              <tr key={a.id} className="border-t border-border">
                <td className="px-3 py-1.5 font-medium">Bus {a.bus_numero}</td><td className="px-3 py-1.5">{a.chauffeur_nom}</td><td className="px-3 py-1.5">{a.trajet_nom}</td>
                <td className="px-3 py-1.5 text-center">{dateFr(a.date_debut)} → {a.date_fin ? dateFr(a.date_fin) : '…'} {a.active && <Badge variant="secondary">en cours</Badge>}{a.a_venir && <Badge variant="outline">à venir</Badge>}</td>
                <td className="px-2 py-1.5 text-right">
                  {responsable && a.active && <Button size="sm" variant="ghost" onClick={() => setDialogue({ terminer: a })}>Terminer</Button>}
                  {responsable && a.a_venir && <Button size="sm" variant="ghost" className="text-destructive" onClick={async () => {
                    try { await api.annulerAffectation(a.id); rafraichir(); toast({ title: 'Affectation annulée' }); }
                    catch (e) { toast({ title: 'Annulation impossible', description: messageErreur(e), variant: 'destructive' }); }
                  }}>Annuler</Button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {dialogue === 'nouvelle' && <NouvelleAffectation onFermer={() => setDialogue(null)}
        onCree={() => { rafraichir(); toast({ title: 'Affectation enregistrée' }); }} />}
      {dialogue?.terminer && <Formulaire titre={`Terminer — Bus ${dialogue.terminer.bus_numero}`} valeurs={{ date_fin: aujourdhui() }} onFermer={() => setDialogue(null)}
        champs={[{ nom: 'date_fin', label: 'Dernier jour', type: 'date', requis: true }]}
        envoyer={async (v) => { await api.terminerAffectation(dialogue.terminer.id, v.date_fin); rafraichir(); toast({ title: 'Affectation terminée' }); }} />}
    </div>
  );
}
