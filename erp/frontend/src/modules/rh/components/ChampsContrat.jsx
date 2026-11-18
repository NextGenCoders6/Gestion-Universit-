/** Champs d'un contrat (préfixe « contrat_ » dans un formulaire de fiche, aucun dans le dialogue de contrat). */
import { useWatch } from 'react-hook-form';
import Champ from '@/components/shared/Champ';
import { TYPES_CONTRAT } from '../lib/format';

export default function ChampsContrat({ register, erreur, control, prefixe = '', requis = false, types = TYPES_CONTRAT }) {
  const n = (champ) => `${prefixe}${champ}`;
  const type = useWatch({ control, name: n('type') });
  return (
    <>
      <Champ nom={n('type')} label="Type de contrat" type="select" requis={requis} register={register}
        erreur={erreur(n('type'))} options={types} vide={requis ? '—' : 'Pas de contrat pour l’instant'} />
      {type && (
        <>
          <Champ nom={n('date_debut')} label="Début du contrat" type="date" requis register={register} erreur={erreur(n('date_debut'))} />
          <Champ nom={n('date_fin')} label="Fin du contrat" type="date" register={register} erreur={erreur(n('date_fin'))}
            aide="Vide : durée indéterminée." />
          {type === 'vacataire'
            ? <Champ nom={n('taux_horaire')} label="Taux horaire (FCFA)" type="number" requis register={register} erreur={erreur(n('taux_horaire'))} />
            : <Champ nom={n('salaire_mensuel')} label="Salaire mensuel (FCFA)" type="number" requis register={register} erreur={erreur(n('salaire_mensuel'))} />}
          <Champ nom={n('rib')} label="RIB" register={register} erreur={erreur(n('rib'))} />
          <Champ nom={n('numero_secu')} label="N° de sécurité sociale" register={register} erreur={erreur(n('numero_secu'))} />
          <Champ nom={n('diplome')} label="Diplôme" register={register} erreur={erreur(n('diplome'))} />
        </>
      )}
    </>
  );
}
