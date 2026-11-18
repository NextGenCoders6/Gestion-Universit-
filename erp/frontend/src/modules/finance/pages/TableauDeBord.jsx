import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';
import GraphiqueTresorerie from '../components/GraphiqueTresorerie';
import { fcfa } from '../lib/format';

function Indicateur({ libelle, valeur, detail }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs uppercase text-muted-foreground">{libelle}</p>
      <p className="text-xl font-bold">{valeur}</p>
      {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
    </div>
  );
}

export default function TableauDeBord() {
  const d = useQuery({ queryKey: ['finance', 'tableau'], queryFn: () => api.tableauDeBord() }).data;
  if (!d) return <p className="text-sm text-muted-foreground">Chargement…</p>;
  const alertes = [
    d.dossiers_en_retard > 0 && { texte: `${d.dossiers_en_retard} dossier(s) en retard : ${fcfa(d.montant_en_retard)} de mensualités échues non réglées.`, lien: '../frais?retard=true' },
    d.dossiers_sans_tarif > 0 && { texte: `${d.dossiers_sans_tarif} dossier(s) à 0 faute de tarif pour leur niveau (Paramètres → Tarifs).`, lien: '../frais' },
    d.trop_percus > 0 && { texte: `${d.trop_percus} trop-perçu(s) : ${fcfa(d.montant_trop_percu)}.`, lien: '../frais' },
  ].filter(Boolean);
  return (
    <div className="space-y-4">
      <PageHeader titre="Tableau de bord" description={`Année ${d.annee_libelle ?? '—'}`} />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Indicateur libelle="Solde de l’année" valeur={fcfa(d.solde)} detail={`${fcfa(d.recettes)} de recettes, ${fcfa(d.depenses)} de dépenses`} />
        <Indicateur libelle="Frais encaissés" valeur={fcfa(d.frais_encaisses)} detail={`sur ${fcfa(d.frais_attendus)} attendus (${d.taux_recouvrement} %)`} />
        <Indicateur libelle="Mensualités en retard" valeur={fcfa(d.montant_en_retard)} detail={`${d.dossiers_en_retard} dossier(s) sur ${d.dossiers}`} />
        <Indicateur libelle="Paie en attente" valeur={fcfa(d.paie_en_attente)} detail="Salaires et vacations restant à payer" />
      </div>
      {alertes.length > 0 && (
        <ul className="space-y-1">
          {alertes.map((a) => (
            <li key={a.texte}><Link to={a.lien} className="flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 hover:underline dark:bg-amber-900/20 dark:text-amber-100">
              <AlertTriangle className="size-4" />{a.texte}</Link></li>
          ))}
        </ul>
      )}
      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-2 font-semibold">Trésorerie des 12 derniers mois</h2>
        <GraphiqueTresorerie donnees={d.tresorerie} />
      </section>
    </div>
  );
}
