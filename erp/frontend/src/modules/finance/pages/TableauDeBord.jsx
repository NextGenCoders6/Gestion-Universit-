import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, BarChart3, CalendarClock, ChevronRight, GraduationCap, Users } from '@/components/ui/icons';
import { Anneau } from '@/components/shared/Graphiques';
import Indicateur from '@/components/shared/Indicateur';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';
import GraphiqueTresorerie from '../components/GraphiqueTresorerie';
import { fcfa } from '../lib/format';

export default function TableauDeBord() {
  const d = useQuery({ queryKey: ['finance', 'tableau'], queryFn: () => api.tableauDeBord() }).data;
  if (!d) return <p className="text-sm text-muted-foreground">Chargement…</p>;
  const alertes = [
    d.dossiers_en_retard > 0 && { texte: `${d.dossiers_en_retard} dossier(s) en retard : ${fcfa(d.montant_en_retard)} de mensualités échues non réglées.`, lien: '../frais?retard=true', ton: 'rouge' },
    d.dossiers_sans_tarif > 0 && { texte: `${d.dossiers_sans_tarif} dossier(s) à 0 faute de tarif pour leur niveau (Paramètres → Tarifs).`, lien: '../frais', ton: 'ambre' },
    d.trop_percus > 0 && { texte: `${d.trop_percus} trop-perçu(s) : ${fcfa(d.montant_trop_percu)}.`, lien: '../frais', ton: 'ambre' },
  ].filter(Boolean);
  const reste = Math.max(0, d.frais_attendus - d.frais_encaisses - d.montant_en_retard);
  return (
    <div className="space-y-6">
      <PageHeader titre="Tableau de bord" description={`Année académique ${d.annee_libelle ?? '—'} · trésorerie, frais et paie.`} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Indicateur libelle="Solde de l’année" valeur={fcfa(d.solde)} icone={BarChart3} ton="primary"
          detail={`${fcfa(d.recettes)} de recettes · ${fcfa(d.depenses)} de dépenses`} />
        <Indicateur libelle="Frais encaissés" valeur={fcfa(d.frais_encaisses)} icone={GraduationCap} ton="success" lien="../frais"
          detail={`sur ${fcfa(d.frais_attendus)} attendus`}
          enfants={(
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
              <div className="h-1.5 rounded-full bg-success" style={{ width: `${Math.min(100, d.taux_recouvrement)}%` }} />
            </div>
          )} />
        <Indicateur libelle="Mensualités en retard" valeur={fcfa(d.montant_en_retard)} icone={CalendarClock} ton="danger" lien="../frais?retard=true"
          detail={`${d.dossiers_en_retard} dossier(s) sur ${d.dossiers}`} />
        <Indicateur libelle="Paie en attente" valeur={fcfa(d.paie_en_attente)} icone={Users} ton="warning" lien="../paie-enseignants"
          detail="Salaires et vacations restant à payer" />
      </div>
      {alertes.length > 0 && (
        <ul className="grid gap-2 lg:grid-cols-2">
          {alertes.map((a) => (
            <li key={a.texte}>
              <Link to={a.lien} className={`group flex items-center gap-3 rounded-xl px-4 py-3 text-sm ring-1 ring-inset transition-colors ${a.ton === 'rouge'
                ? 'bg-red-50 text-red-800 ring-red-600/15 hover:bg-red-100/70 dark:bg-red-500/10 dark:text-red-200'
                : 'bg-amber-50 text-amber-900 ring-amber-600/20 hover:bg-amber-100/70 dark:bg-amber-500/10 dark:text-amber-100'}`}>
                <AlertTriangle className="size-4 shrink-0" /><span className="flex-1">{a.texte}</span>
                <ChevronRight className="size-4 opacity-50 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </li>
          ))}
        </ul>
      )}
      <div className="grid gap-4 xl:grid-cols-3">
        <section className="carte p-5 xl:col-span-2">
          <h2 className="font-semibold tracking-tight">Trésorerie des 12 derniers mois</h2>
          <p className="mb-4 text-sm text-muted-foreground">Recettes et dépenses du journal, annulations exclues.</p>
          <GraphiqueTresorerie donnees={d.tresorerie} />
        </section>
        <section className="carte p-5">
          <h2 className="font-semibold tracking-tight">Recouvrement des frais</h2>
          <p className="mb-5 text-sm text-muted-foreground">Situation des {d.dossiers} dossiers de l’année.</p>
          <Anneau titre="Recouvrement des frais de scolarité" centre={`${d.taux_recouvrement} %`} sousCentre="recouvré" formater={fcfa}
            segments={[
              { libelle: 'Encaissé', valeur: d.frais_encaisses, couleur: 'hsl(var(--success))' },
              { libelle: 'En retard', valeur: d.montant_en_retard, couleur: 'hsl(var(--destructive))' },
              { libelle: 'À venir', valeur: reste, couleur: 'hsl(var(--muted-foreground) / 0.35)' },
            ]} />
        </section>
      </div>
    </div>
  );
}
