import { FIELD } from '../useAvailabilityCheck';

const COLORS = {
  [FIELD.CHECKING]: 'text-muted',
  [FIELD.OK]:       'text-green-400',
  [FIELD.TAKEN]:    'text-red-400',
  [FIELD.INVALID]:  'text-red-400',
};

/** Inline availability indicator rendered under an email / CNIC input. */
export default function FieldStatus({ state, message }) {
  if (state === FIELD.IDLE || !message) return null;
  return <p className={`text-[11px] mt-1 ${COLORS[state] ?? 'text-muted'}`}>{message}</p>;
}
