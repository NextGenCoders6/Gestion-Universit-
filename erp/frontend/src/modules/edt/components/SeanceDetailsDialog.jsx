/** Fiche d'une séance et ses actions (publier, dépublier, reporter, annuler, modifier, supprimer). */
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { BookOpen, CalendarClock, Clock, User, Users } from '@/components/ui/icons';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import { useToast } from '@/hooks/use-toast';
import { confirmer } from '@/lib/confirmer';
import { erreursServeur } from '@/lib/erreurs';
import { formatDate } from '@/lib/utils';
import * as api from '../api';
import { STATUT_COLORS, STATUT_LABELS } from '../lib/constantes';

function Ligne({ icone: Icone, children }) {
  return (
    <div className="flex items-center gap-2 text-sm text-foreground">
      <Icone className="size-4 shrink-0 text-muted-foreground" />
      <span>{children}</span>
    </div>
  );
}

export default function SeanceDetailsDialog({ seance, peutGerer, onFermer, onModifier }) {
  const client = useQueryClient();
  const { toast } = useToast();
  const [report, setReport] = useState(null);
  const [erreur, setErreur] = useState(null);

  const action = useMutation({
    mutationFn: ({ fn }) => fn(),
    onSuccess: (_, { message }) => {
      client.invalidateQueries({ queryKey: ['edt'] });
      toast({ title: message });
      setReport(null);
      onFermer();
    },
    onError: (e) => {
      const { champs, global } = erreursServeur(e);
      setErreur(Object.values(champs)[0] ?? global);
    },
  });

  if (!seance) return null;
  const { jour, debut, fin } = seance.creneau_effectif;
  const statut = STATUT_COLORS[seance.statut] ?? {};
  const lancer = (fn, message) => { setErreur(null); action.mutate({ fn, message }); };

  return (
    <Dialog open onOpenChange={(o) => { if (!o) { setReport(null); setErreur(null); onFermer(); } }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{seance.ec_code} — {seance.ec_libelle}</DialogTitle>
          <DialogDescription>{seance.libelle || `${seance.type_seance} · ${seance.classe_libelle}`}</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Badge variant="outline" className={`${statut.bg} ${statut.text}`}>{STATUT_LABELS[seance.statut]}</Badge>
          <Ligne icone={Clock}>{formatDate(jour)} · {debut} → {fin}</Ligne>
          {seance.statut === 'Reportée' && (
            <Ligne icone={CalendarClock}>Initialement le {formatDate(seance.date_seance)} à {seance.heure_debut}</Ligne>
          )}
          <Ligne icone={Users}>{seance.classe_libelle}</Ligne>
          <Ligne icone={User}>{seance.enseignant_nom}</Ligne>
          <Ligne icone={BookOpen}>{seance.type_seance}{seance.seance_liee ? ' · cours mutualisé' : ''}</Ligne>
        </div>

        {peutGerer && report && (
          <div className="space-y-3 rounded-lg border border-border p-3">
            <p className="text-sm font-semibold">Reporter la séance</p>
            <div className="space-y-1.5">
              <Label htmlFor="date-report">Nouvelle date</Label>
              <Input id="date-report" type="date" value={report.date_report}
                onChange={(e) => setReport({ ...report, date_report: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label htmlFor="debut-report">Début</Label>
                <Input id="debut-report" type="time" value={report.heure_debut_report}
                  onChange={(e) => setReport({ ...report, heure_debut_report: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="fin-report">Fin</Label>
                <Input id="fin-report" type="time" value={report.heure_fin_report}
                  onChange={(e) => setReport({ ...report, heure_fin_report: e.target.value })} />
              </div>
            </div>
            <Button size="sm" disabled={action.isPending}
              onClick={() => lancer(() => api.reporterSeance(seance.id, report), 'Séance reportée')}>
              Confirmer le report
            </Button>
          </div>
        )}

        <ErreurFormulaire message={erreur} />

        {peutGerer && !report && (
          <div className="flex flex-wrap gap-2 pt-2">
            {seance.statut === 'brouillon' && (
              <Button size="sm" disabled={action.isPending}
                onClick={() => lancer(() => api.publierSeance(seance.id), 'Séance publiée')}>Publier</Button>
            )}
            {seance.statut === 'Confirmée' && (
              <>
                <Button size="sm" variant="outline"
                  onClick={() => setReport({ date_report: jour, heure_debut_report: debut, heure_fin_report: fin })}>
                  Reporter
                </Button>
                <Button size="sm" variant="outline" disabled={action.isPending}
                  onClick={() => lancer(() => api.depublierSeance(seance.id), 'Séance repassée en brouillon')}>
                  Dépublier
                </Button>
              </>
            )}
            {['brouillon', 'Confirmée'].includes(seance.statut) && (
              <>
                <Button size="sm" variant="outline" onClick={() => onModifier(seance)}>Modifier</Button>
                <Button size="sm" variant="outline" disabled={action.isPending}
                  onClick={() => lancer(() => api.modifierSeance(seance.id, { statut: 'Annulée' }), 'Séance annulée')}>
                  Annuler la séance
                </Button>
              </>
            )}
            <Button size="sm" variant="destructive" disabled={action.isPending}
              onClick={async () => {
                const ok = await confirmer({ titre: 'Supprimer cette séance ?', description: 'Cette action est définitive.',
                  libelleConfirmer: 'Supprimer', destructif: true });
                if (ok) lancer(() => api.supprimerSeance(seance.id), 'Séance supprimée');
              }}>
              Supprimer
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
