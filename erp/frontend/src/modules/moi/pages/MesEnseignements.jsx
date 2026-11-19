import { useQuery } from '@tanstack/react-query';
import PageHeader from '@/components/shared/PageHeader';
import BarreAvancement, { LegendeAvancement } from '@/modules/edt/components/BarreAvancement';
import * as api from '../api';

const pct = (v, max) => (max ? Math.min(100, Math.round((v / max) * 100)) : 0);

export default function MesEnseignements() {
  const affectations = useQuery({ queryKey: ['moi', 'enseignements'], queryFn: api.mesEnseignements });
  return (
    <div className="space-y-4">
      <PageHeader titre="Mes enseignements" description="Vos affectations et leur avancement."><LegendeAvancement /></PageHeader>
      {affectations.data?.length === 0 && <p className="text-sm text-muted-foreground">Aucune affectation pour l’instant.</p>}
      <div className="grid gap-3 md:grid-cols-2">
        {(affectations.data ?? []).map((a) => (
          <article key={a.id} className="space-y-2 carte p-4">
            <h3 className="font-semibold">{a.ec_code} — {a.ec_libelle}</h3>
            <p className="text-xs text-muted-foreground">{a.classe_libelle} · {a.type_seance ?? 'tous types'}</p>
            <BarreAvancement faites={pct(a.heures_effectuees, a.heures_prevues)} planifiees={pct(a.heures_consommees, a.heures_prevues)}
              label={`Avancement de ${a.ec_code}`} valeur={`${a.heures_effectuees} h faites sur ${a.heures_prevues} h`} />
            <p className="text-xs text-muted-foreground">{a.heures_effectuees} h faites · {a.heures_consommees} h planifiées · {a.heures_prevues} h prévues</p>
          </article>
        ))}
      </div>
    </div>
  );
}
