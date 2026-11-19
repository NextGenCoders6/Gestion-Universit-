import { useParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import * as api from '../api';
import FicheRH from '../components/FicheRH';
import { heures, montant } from '../lib/format';

function etatVacation(a) {
  if (a.vacation) return <Badge variant="secondary">Confirmée · {montant(a.vacation.montant)}</Badge>;
  if (a.motif_blocage) return <span className="text-xs text-muted-foreground">{a.motif_blocage}</span>;
  return a.terminee ? <Badge>À confirmer par la faculté</Badge> : <span className="text-xs text-muted-foreground">En cours</span>;
}

export default function FicheEnseignant() {
  const { id } = useParams();
  return (
    <FicheRH id={id} cle="enseignant" charger={api.ficheEnseignant} retour="Tous les enseignants" enseignant
      infosRole={(f) => [['Département', `${f.departement_libelle} (${f.faculte})`], ['Grade', f.grade],
        ['Chef de département', f.est_chef ? 'Oui' : 'Non']]}>
      {(f) => (
        <section className="space-y-2 carte p-4">
          <h2 className="font-semibold">Enseignements de l’année et vacations</h2>
          {f.affectations.length === 0 && <p className="text-sm text-muted-foreground">Aucune affectation cette année.</p>}
          <table className="w-full text-sm">
            <tbody>
              {f.affectations.map((a) => (
                <tr key={a.affectation} className="border-t border-border">
                  <td className="py-1.5">{a.ec_code} — {a.ec_libelle}<div className="text-xs text-muted-foreground">{a.classe_libelle}</div></td>
                  <td className="text-center">{heures(a.heures_effectuees)} / {heures(a.heures_prevues)}</td>
                  <td className="text-right">{etatVacation(a)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </FicheRH>
  );
}
