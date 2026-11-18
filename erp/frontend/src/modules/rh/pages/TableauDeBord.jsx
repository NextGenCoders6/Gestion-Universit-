import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';
import { dateFr } from '../lib/format';

function Indicateur({ libelle, valeur, detail, lien }) {
  const contenu = (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs uppercase text-muted-foreground">{libelle}</p>
      <p className="text-2xl font-bold">{valeur ?? '—'}</p>
      {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
    </div>
  );
  return lien ? <Link to={lien} className="block hover:opacity-90">{contenu}</Link> : contenu;
}

export default function TableauDeBord() {
  const d = useQuery({ queryKey: ['rh', 'tableau'], queryFn: api.tableauDeBord }).data;
  return (
    <div className="space-y-4">
      <PageHeader titre="Tableau de bord" description="Effectifs sous contrat, échéances et vacations." />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Indicateur libelle="Enseignants actifs" valeur={d?.enseignants_actifs} lien="../enseignants?actif=true"
          detail={d && `${d.enseignants_permanents} permanent(s), ${d.enseignants_vacataires} vacataire(s), ${d.chefs_departement} chef(s) de département`} />
        <Indicateur libelle="Personnel actif" valeur={d?.personnel_actif} lien="../personnel?actif=true"
          detail={d?.personnel_par_fonction?.map((f) => `${f.n} ${f.libelle.toLowerCase()}`).join(', ')} />
        <Indicateur libelle="Vacations à confirmer" valeur={d?.vacations_a_confirmer} lien="../vacations"
          detail="Affectations terminées, en attente de la faculté" />
        <Indicateur libelle="Sans contrat en cours" valeur={d?.personnes_sans_contrat_en_cours} lien="../contrats?etat=expire"
          detail="Contrat expiré, à renouveler ou à clore" />
      </div>
      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-2 font-semibold">Contrats arrivant à échéance (30 jours)</h2>
        {d?.contrats_a_echeance?.length === 0 && <p className="text-sm text-muted-foreground">Aucun.</p>}
        <ul className="space-y-1 text-sm">
          {(d?.contrats_a_echeance ?? []).map((c) => (
            <li key={c.id}>{c.personne_nom} · {c.type === 'permanent' ? 'permanent' : 'vacataire'} · fin le <strong>{dateFr(c.date_fin)}</strong></li>
          ))}
        </ul>
      </section>
    </div>
  );
}
