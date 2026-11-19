/** Trombinoscope : les enseignants de la classe de l'étudiant et leurs enseignements. */
import { useQuery } from '@tanstack/react-query';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';

const initiales = (nom) => nom.split(' ').filter(Boolean).slice(0, 2).map((m) => m[0]).join('').toUpperCase();

export default function MesEnseignants() {
  const enseignants = useQuery({ queryKey: ['moi', 'enseignants'], queryFn: api.mesEnseignants });
  return (
    <div className="space-y-4">
      <PageHeader titre="Mes enseignants" description="Les enseignants de votre classe cette année." />
      {enseignants.data?.length === 0 && <p className="text-sm text-muted-foreground">Aucun enseignant affecté pour l’instant.</p>}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {(enseignants.data ?? []).map((e) => (
          <article key={e.id} className="flex gap-3 carte p-4">
            <Avatar className="size-12">
              {e.photo && <AvatarImage src={e.photo} alt="" />}
              <AvatarFallback>{initiales(e.nom_complet)}</AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <h3 className="font-semibold">{e.nom_complet}</h3>
              {e.grade && <p className="text-xs text-muted-foreground">{e.grade}</p>}
              <ul className="mt-1 text-sm">{e.ecs.map((x) => <li key={x.id}>{x.code} — {x.libelle}</li>)}</ul>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
