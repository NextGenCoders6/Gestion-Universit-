import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Plus } from '@/components/ui/icons';
import DataTable from '@/components/shared/DataTable';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import Formulaire from '../Formulaire';
import { useEstResponsableLogistique } from '../hooks';

const CHAMPS = [
  { nom: 'nom', label: 'Nom', requis: true }, { nom: 'depart', label: 'Départ', requis: true },
  { nom: 'destination', label: 'Destination', requis: true },
  { nom: 'heure_depart', label: 'Heure de départ', type: 'time', requis: true },
  { nom: 'heure_arrivee', label: 'Heure d’arrivée', type: 'time', requis: true },
];

export default function Trajets() {
  const client = useQueryClient();
  const { toast } = useToast();
  const responsable = useEstResponsableLogistique();
  const trajets = useQuery({ queryKey: ['logistique', 'trajets'], queryFn: api.listerTrajets });
  const [dialogue, setDialogue] = useState(null);
  const rafraichir = () => client.invalidateQueries({ queryKey: ['logistique'] });
  const colonnes = [
    { key: 'nom', label: 'Trajet' },
    { key: 'parcours', label: 'Parcours', render: (t) => `${t.depart} → ${t.destination}` },
    { key: 'horaire', label: 'Horaire', render: (t) => `${t.heure_depart.slice(0, 5)} – ${t.heure_arrivee.slice(0, 5)}` },
  ];
  return (
    <div className="space-y-4">
      <PageHeader titre="Trajets" description="Lignes desservies par les bus.">
        {responsable && <Button onClick={() => setDialogue('nouveau')}><Plus /> Nouveau trajet</Button>}
      </PageHeader>
      <DataTable columns={colonnes} data={trajets.data ?? []} isLoading={trajets.isLoading} emptyMessage="Aucun trajet." libelleLigne={(t) => t.nom}
        onEdit={responsable ? (t) => setDialogue({ modifier: t }) : undefined}
        onDelete={responsable ? async (t) => { try { await api.supprimerTrajet(t.id); rafraichir(); } catch (e) { toast({ title: 'Suppression impossible', description: erreursServeur(e).global, variant: 'destructive' }); } } : undefined} />
      {dialogue === 'nouveau' && <Formulaire titre="Nouveau trajet" champs={CHAMPS} onFermer={() => setDialogue(null)}
        envoyer={async (v) => { await api.creerTrajet(v); rafraichir(); toast({ title: 'Trajet ajouté' }); }} />}
      {dialogue?.modifier && <Formulaire titre={dialogue.modifier.nom} champs={CHAMPS} onFermer={() => setDialogue(null)}
        valeurs={{ ...dialogue.modifier, heure_depart: dialogue.modifier.heure_depart.slice(0, 5), heure_arrivee: dialogue.modifier.heure_arrivee.slice(0, 5) }}
        envoyer={async (v) => { await api.modifierTrajet(dialogue.modifier.id, v); rafraichir(); toast({ title: 'Trajet modifié' }); }} />}
    </div>
  );
}
