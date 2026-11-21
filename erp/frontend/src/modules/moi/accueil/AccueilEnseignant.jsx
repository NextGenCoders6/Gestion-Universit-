/** Accueil de l'enseignant : heures de la semaine, avancement, classes, documents, prochaines séances. */
import { useQuery } from '@tanstack/react-query';
import { CalendarDays, Clock, FileText, School } from '@/components/ui/icons';
import Indicateur from '@/components/shared/Indicateur';
import { bornesSemaine } from '@/lib/dates';
import { dateFr } from '@/modules/finance/lib/format';
import BarreAvancement from '@/modules/edt/components/BarreAvancement';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import { bilanEnseignements, heuresSeances, prochainesSeances, regrouperMutualisees } from './calculs';
import { INDISPONIBLE, quatorzeJours } from './commun';
import EnTeteAccueil from './EnTeteAccueil';
import LigneSeance from './LigneSeance';
import ListeCarte from './ListeCarte';

const pct = (v, max) => (max ? Math.min(100, Math.round((v / max) * 100)) : 0);
const heures = (n) => `${n.toLocaleString('fr-FR')} h`;

/** Valeur d'un indicateur selon l'état de sa requête. */
function selon(requete, calcul) {
  if (requete.isPending) return { valeur: '…' };
  if (requete.isError) return { valeur: '—', detail: INDISPONIBLE };
  return calcul(requete.data);
}

export default function AccueilEnseignant() {
  const nomComplet = useAuthStore((s) => s.user?.nom_complet);
  const maintenant = new Date();
  const semaine = bornesSemaine(maintenant);
  const aVenir = quatorzeJours(maintenant);

  const seancesSemaine = useQuery({ queryKey: ['moi', 'planning', semaine],
    queryFn: () => api.monPlanning({ date_debut: semaine.debut, date_fin: semaine.fin }) });
  const seancesAVenir = useQuery({ queryKey: ['moi', 'planning', aVenir],
    queryFn: () => api.monPlanning({ date_debut: aVenir.debut, date_fin: aVenir.fin }) });
  const affectations = useQuery({ queryKey: ['moi', 'enseignements'], queryFn: api.mesEnseignements });
  const documents = useQuery({ queryKey: ['moi', 'documents'], queryFn: api.mesDocuments });

  const bilan = bilanEnseignements(affectations.data);
  const prochaines = prochainesSeances(regrouperMutualisees(seancesAVenir.data), maintenant);

  return (
    <div className="space-y-6">
      <EnTeteAccueil nomComplet={nomComplet} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Indicateur libelle="Cours cette semaine" icone={CalendarDays} lien="/moi/planning"
          {...selon(seancesSemaine, (d) => ({ valeur: heures(heuresSeances(regrouperMutualisees(d))), detail: `Semaine du ${dateFr(semaine.debut)}` }))} />
        <Indicateur libelle="Heures faites" icone={Clock} lien="/moi/enseignements"
          {...selon(affectations, () => ({ valeur: `${heures(bilan.faites)} / ${heures(bilan.prevues)}`, detail: 'Sur l’ensemble de vos affectations' }))} />
        <Indicateur libelle="Classes" icone={School} lien="/moi/enseignements"
          {...selon(affectations, () => ({ valeur: String(bilan.classes) }))} />
        <Indicateur libelle="Documents déposés" icone={FileText} lien="/moi/documents"
          {...selon(documents, (d) => ({ valeur: String(d.length) }))} />
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ListeCarte titre="Prochaines séances" lien="/moi/planning" chargement={seancesAVenir.isPending}
          erreur={seancesAVenir.isError && INDISPONIBLE} vide={prochaines.length === 0 && 'Aucune séance dans les 14 prochains jours.'}>
          <ul className="divide-y divide-border">
            {prochaines.map((s) => <LigneSeance key={s.id} seance={s} detail={s.classes.join(' · ')} />)}
          </ul>
        </ListeCarte>
        <ListeCarte titre="Avancement" lien="/moi/enseignements" chargement={affectations.isPending}
          erreur={affectations.isError && INDISPONIBLE} vide={affectations.data?.length === 0 && 'Aucune affectation pour l’instant.'}>
          <ul className="space-y-3">
            {(affectations.data ?? []).map((a) => {
              // Classe et type de séance : un même EC peut être donné dans deux classes, ou en CM et en TD.
              const precision = [a.classe_libelle, a.type_seance].filter(Boolean).join(' · ');
              return (
                <li key={a.id} className="space-y-1.5">
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-foreground">{a.ec_code} — {a.ec_libelle}</p>
                      {precision && <p className="truncate text-xs text-muted-foreground">{precision}</p>}
                    </div>
                    <p className="chiffres shrink-0 text-xs text-muted-foreground">{a.heures_effectuees} / {a.heures_prevues} h</p>
                  </div>
                  <BarreAvancement faites={pct(a.heures_effectuees, a.heures_prevues)} planifiees={pct(a.heures_consommees, a.heures_prevues)}
                    label={precision ? `Avancement de ${a.ec_code} — ${precision}` : `Avancement de ${a.ec_code}`}
                    valeur={`${a.heures_effectuees} h faites sur ${a.heures_prevues} h`} />
                </li>
              );
            })}
          </ul>
        </ListeCarte>
      </div>
    </div>
  );
}
