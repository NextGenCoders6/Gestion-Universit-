import { useQuery } from '@tanstack/react-query';
import DataTable from '@/components/shared/DataTable';
import PageHeader from '@/components/shared/PageHeader';
import Selecteur from '@/components/shared/Selecteur';
import { useSearchParams } from 'react-router-dom';
import * as api from '../api';
import { dateFr, ETATS_CONTRAT, montant } from '../lib/format';
import Pastille from '@/components/shared/Pastille';

const VUES = [
  { valeur: 'echeance', libelle: 'À échéance (30 jours)' },
  { valeur: 'en_cours', libelle: 'En cours' },
  { valeur: 'expire', libelle: 'Expirés' },
  { valeur: 'a_venir', libelle: 'À venir' },
];

export default function Contrats() {
  const [params, setParams] = useSearchParams();
  const vue = params.get('etat') || 'echeance';
  const requete = vue === 'echeance' ? { echeance: 30, page_size: 200 } : { etat: vue, page_size: 200 };
  const liste = useQuery({ queryKey: ['rh', 'contrats', requete], queryFn: () => api.listerContrats(requete) });
  const colonnes = [
    { key: 'personne_nom', label: 'Personne', render: (c) => <>{c.personne_nom}<div className="text-xs text-muted-foreground">{c.role === 'enseignant' ? 'Enseignant' : 'Personnel'}</div></> },
    { key: 'type', label: 'Type', render: (c) => (c.type === 'permanent' ? 'Permanent' : 'Vacataire') },
    { key: 'periode', label: 'Période', render: (c) => `${dateFr(c.date_debut)} → ${c.date_fin ? dateFr(c.date_fin) : 'indéterminée'}` },
    { key: 'montant', label: 'Rémunération', render: (c) => (c.type === 'permanent' ? `${montant(c.salaire_mensuel)} / mois` : `${montant(c.taux_horaire)} / h`) },
    { key: 'etat', label: 'État', render: (c) => <Pastille ton={{ en_cours: 'vert', a_venir: 'bleu' }[c.etat] ?? 'gris'}>{ETATS_CONTRAT[c.etat]}</Pastille> },
  ];
  return (
    <div className="space-y-4">
      <PageHeader titre="Contrats" description="Échéances, contrats en cours, expirés ou à venir." />
      <Selecteur id="vue" label="Afficher" valeur={vue} options={VUES} vide="—" className="max-w-xs"
        onChange={(v) => setParams(v ? { etat: v } : {}, { replace: true })} />
      <DataTable columns={colonnes} data={liste.data?.results ?? []} isLoading={liste.isLoading} isError={liste.isError}
        emptyMessage="Aucun contrat." />
    </div>
  );
}
