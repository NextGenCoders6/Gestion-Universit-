/** Notes de l'étudiant par année et par semestre ; moyenne et décision une fois le semestre délibéré. */
import { useQuery } from '@tanstack/react-query';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';

const note = (v) => (v === null || v === undefined ? '—' : Number(v).toFixed(2).replace('.', ','));

function Semestre({ s }) {
  const r = s.resultat;
  return (
    <section className="space-y-2 rounded-lg border border-border bg-card p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{s.semestre}</h3>
        {r ? (
          <p className="text-sm">
            <span className={`mr-2 rounded px-2 py-0.5 text-xs font-semibold ${r.decision === 'ADMIS' ? 'bg-primary/10 text-primary' : 'bg-destructive/10 text-destructive'}`}>
              {r.decision}
            </span>
            {note(r.moyenne)} / 20 · {r.credits_obtenus}/{r.credits_totaux} crédits{r.mention !== 'NÉANT' ? ` · ${r.mention}` : ''}
          </p>
        ) : <p className="text-sm text-muted-foreground">En attente de délibération</p>}
      </header>
      <table className="w-full text-sm">
        <thead className="text-xs text-muted-foreground"><tr>
          <th className="py-1 text-left">Élément constitutif</th><th>Crédits</th><th>Devoir</th><th>Session</th><th>SR</th><th>Moyenne</th>
        </tr></thead>
        <tbody>
          {s.ues.flatMap((u) => [
            <tr key={`ue-${u.id}`} className="border-t border-border bg-muted/30">
              <td className="py-1 font-medium" colSpan={5}>{u.code} — {u.libelle}</td>
              <td className="text-center font-semibold">{r ? note(u.moyenne_ue) : ''}</td>
            </tr>,
            ...u.ecs.map((e) => (
              <tr key={e.id} className="border-t border-border/60">
                <td className="py-1 pl-3">{e.libelle}</td>
                <td className="text-center">{e.credits}</td>
                <td className="text-center">{e.absent ? 'ABS' : note(e.devoir)}</td>
                <td className="text-center">{e.absent ? 'ABS' : note(e.session)}</td>
                <td className="text-center">{note(e.sr)}</td>
                <td className="text-center font-medium">{note(e.note)}</td>
              </tr>
            )),
          ])}
        </tbody>
      </table>
    </section>
  );
}

export default function MesNotes() {
  const notes = useQuery({ queryKey: ['moi', 'notes'], queryFn: api.mesNotes });
  return (
    <div className="space-y-4">
      <PageHeader titre="Mes notes" description={notes.data ? `Matricule ${notes.data.matricule}` : undefined} />
      {notes.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
      {notes.data?.inscriptions?.length === 0 && <p className="text-sm text-muted-foreground">Aucune inscription pour l’instant.</p>}
      {(notes.data?.inscriptions ?? []).map((i) => (
        <div key={i.inscription} className="space-y-3">
          <h2 className="text-lg font-semibold">{i.classe}</h2>
          {i.resultats_masques && (
            <p role="status" className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-900/20 dark:text-amber-100">
              {i.message_resultats}
            </p>
          )}
          <div className="grid gap-3 xl:grid-cols-2">
            {i.semestres.map((s) => <Semestre key={s.semestre} s={s} />)}
          </div>
        </div>
      ))}
    </div>
  );
}
