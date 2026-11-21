/** Accueil de l'étudiant : dernier résultat, cours de la semaine, frais, prochains cours et enseignants. */
import { useQuery } from '@tanstack/react-query';
import { CalendarClock, CalendarDays, GraduationCap, Tag } from '@/components/ui/icons';
import Indicateur from '@/components/shared/Indicateur';
import { bornesSemaine } from '@/lib/dates';
import { dateFr } from '@/modules/finance/lib/format';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import { dernierResultat, dossierCourant, heuresSeances, prochainesSeances } from './calculs';
import EnTeteAccueil from './EnTeteAccueil';
import LigneSeance from './LigneSeance';
import ListeCarte from './ListeCarte';
import { INDISPONIBLE, quatorzeJours } from './commun';

/** Montant en grand, unité en plus petit : la valeur tient sur une ligne dans les cartes étroites. */
const montant = (v) => (
  <>{Number(v ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })}{' '}
    <span className="text-base font-medium text-muted-foreground">FCFA</span></>
);

const moyenne = (v) => `${v.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} /20`;

function indicateurResultat(notes) {
  if (notes.isPending) return { valeur: '…' };
  if (notes.isError) return { valeur: '—', detail: INDISPONIBLE };
  const r = dernierResultat(notes.data);
  if (!r) return { valeur: '—', detail: 'Pas encore de résultat délibéré.' };
  if (r.masque !== undefined) return { valeur: '—', detail: r.masque };
  return { valeur: moyenne(r.moyenne), detail: `${r.semestre} · ${r.decision}` };
}

function indicateursFrais(frais) {
  if (frais.isPending) return [{ valeur: '…' }, { valeur: '…' }];
  if (frais.isError) return [{ valeur: '—', detail: INDISPONIBLE }, { valeur: '—', detail: INDISPONIBLE }];
  const d = dossierCourant(frais.data);
  if (!d) return [{ valeur: '—', detail: 'Aucun dossier de frais.' }, { valeur: '—', detail: 'Aucun dossier de frais.' }];
  const reste = { valeur: montant(d.reste), detail: d.classe_libelle };
  if (d.en_retard) return [reste, { valeur: montant(d.montant_en_retard), detail: 'Une mensualité en retard', ton: 'danger' }];
  const p = d.prochaine_echeance;
  return [reste, p
    ? { valeur: montant(p.montant - p.paye), detail: `avant le ${dateFr(p.date_limite)}` }
    : { valeur: '—', detail: 'Aucune échéance à venir.' }];
}

export default function AccueilEtudiant() {
  const nomComplet = useAuthStore((s) => s.user?.nom_complet);
  const maintenant = new Date();
  const semaine = bornesSemaine(maintenant);
  const aVenir = quatorzeJours(maintenant);

  const notes = useQuery({ queryKey: ['moi', 'notes'], queryFn: api.mesNotes });
  const coursSemaine = useQuery({ queryKey: ['moi', 'planning-etudiant', semaine],
    queryFn: () => api.monPlanningEtudiant({ date_debut: semaine.debut, date_fin: semaine.fin }) });
  const coursAVenir = useQuery({ queryKey: ['moi', 'planning-etudiant', aVenir],
    queryFn: () => api.monPlanningEtudiant({ date_debut: aVenir.debut, date_fin: aVenir.fin }) });
  const enseignants = useQuery({ queryKey: ['moi', 'enseignants'], queryFn: api.mesEnseignants });
  const frais = useQuery({ queryKey: ['moi', 'frais'], queryFn: api.mesFrais });

  const resultat = indicateurResultat(notes);
  const [reste, echeance] = indicateursFrais(frais);
  const heures = coursSemaine.isPending ? { valeur: '…' }
    : coursSemaine.isError ? { valeur: '—', detail: INDISPONIBLE }
      : { valeur: `${heuresSeances(coursSemaine.data).toLocaleString('fr-FR')} h`, detail: `Semaine du ${dateFr(semaine.debut)}` };
  const prochains = prochainesSeances(coursAVenir.data, maintenant);

  return (
    <div className="space-y-6">
      <EnTeteAccueil nomComplet={nomComplet} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Indicateur libelle="Moyenne du dernier semestre" icone={GraduationCap} lien="/moi/notes" {...resultat} />
        <Indicateur libelle="Cours cette semaine" icone={CalendarDays} lien="/moi/planning" {...heures} />
        <Indicateur libelle="Reste à payer" icone={Tag} lien="/moi/frais" {...reste} />
        <Indicateur libelle="Prochaine échéance" icone={CalendarClock} lien="/moi/frais" {...echeance} />
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ListeCarte titre="Prochains cours" lien="/moi/planning" chargement={coursAVenir.isPending}
          erreur={coursAVenir.isError && INDISPONIBLE} vide={prochains.length === 0 && 'Aucun cours dans les 14 prochains jours.'}>
          <ul className="divide-y divide-border">
            {prochains.map((s) => <LigneSeance key={s.id} seance={s} detail={s.enseignant_nom} />)}
          </ul>
        </ListeCarte>
        <ListeCarte titre="Mes enseignants" lien="/moi/enseignants" chargement={enseignants.isPending}
          erreur={enseignants.isError && INDISPONIBLE} vide={enseignants.data?.length === 0 && 'Aucun enseignant pour l’instant.'}>
          <ul className="divide-y divide-border">
            {(enseignants.data ?? []).map((e) => (
              <li key={e.id} className="py-2.5">
                <p className="font-medium text-foreground">{e.nom_complet}</p>
                <p className="text-xs text-muted-foreground">
                  {[e.grade, e.ecs.map((ec) => ec.code).join(', ')].filter(Boolean).join(' · ')}
                </p>
              </li>
            ))}
          </ul>
        </ListeCarte>
      </div>
    </div>
  );
}
