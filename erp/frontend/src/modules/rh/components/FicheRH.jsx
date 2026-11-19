/** Fiche d'un enseignant ou d'un employé : identité, rôle, contrats, et contenu propre au rôle. */
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import { erreursServeur } from '@/lib/erreurs';
import { dateFr, libelleContrat } from '../lib/format';
import SectionContrats from './SectionContrats';

function Info({ label, children }) {
  return <div><dt className="text-xs text-muted-foreground">{label}</dt><dd className="text-sm font-medium">{children || '—'}</dd></div>;
}

export default function FicheRH({ id, cle, charger, retour, enseignant, infosRole, children }) {
  const fiche = useQuery({ queryKey: ['rh', cle, id], queryFn: () => charger(id) });
  if (fiche.isLoading) return <p className="text-sm text-muted-foreground">Chargement…</p>;
  if (fiche.isError) return <p className="text-sm text-destructive">{erreursServeur(fiche.error).global}</p>;
  const f = fiche.data;
  const p = f.personne;
  return (
    <div className="space-y-4">
      <Link to=".." relative="path" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> {retour}
      </Link>
      <PageHeader titre={f.nom_complet} description={`Matricule ${f.matricule} · ${libelleContrat(f.contrat_en_cours)}`} />
      <dl className="grid grid-cols-2 gap-3 carte p-4 sm:grid-cols-4">
        <Info label="Genre">{p.genre === 'F' ? 'Féminin' : 'Masculin'}</Info>
        <Info label="Date de naissance">{p.date_naissance && dateFr(p.date_naissance)}</Info>
        <Info label="E-mail">{p.email}</Info>
        <Info label="Téléphone">{p.telephone}</Info>
        {infosRole(f).map(([label, valeur]) => <Info key={label} label={label}>{valeur}</Info>)}
      </dl>
      <SectionContrats personne={f.id} contrats={f.contrats} enseignant={enseignant} />
      {children?.(f)}
    </div>
  );
}
