import { useCallback, useEffect, useRef, useState } from 'react';
import { checkEmail, checkCnic } from './api';

export const FIELD = {
  IDLE:     'idle',      // field untouched or empty
  CHECKING: 'checking',  // request in flight (debounce done)
  OK:       'ok',        // available + valid format
  TAKEN:    'taken',     // format OK but already registered
  INVALID:  'invalid',   // bad format (client regex, or server valid_format=false)
};

const DEBOUNCE_MS = 600;

/**
 * Debounced "is this value already registered?" check for a single field.
 *
 * RegisterPage and the admin's create-authority modal both need this for email
 * and CNIC, and each had its own near-identical copy of the timers, the
 * last-checked short-circuit, the five status constants and the submit gate.
 *
 * @param value          current field value (controlled input)
 * @param check          (normalised) => Promise<{ available, valid_format, reason }>
 * @param normalize      raw value → the form sent to the API
 * @param pattern        client-side format guard, checked before any request
 * @param invalidMessage shown when `pattern` fails
 * @param okMessage      shown when the value is free
 * @param takenMessage   fallback when the server gives no `reason`
 */
export function useAvailabilityCheck({
  value,
  check,
  normalize = (v) => (v ?? '').trim(),
  pattern,
  invalidMessage,
  okMessage,
  takenMessage,
}) {
  const [status, setStatus] = useState({ state: FIELD.IDLE, message: '' });

  const timer = useRef(null);
  const lastChecked = useRef('');
  const checkRef = useRef(check);
  checkRef.current = check;

  const run = useCallback(async (raw) => {
    const v = normalize(raw);

    if (!v) {
      setStatus({ state: FIELD.IDLE, message: '' });
      return;
    }
    if (pattern && !pattern.test(v)) {
      setStatus({ state: FIELD.INVALID, message: invalidMessage });
      return;
    }
    if (v === lastChecked.current) return;

    lastChecked.current = v;
    setStatus({ state: FIELD.CHECKING, message: 'Checking availability…' });

    try {
      const { data } = await checkRef.current(v);
      if (!data.valid_format)  setStatus({ state: FIELD.INVALID, message: data.reason ?? invalidMessage });
      else if (data.available) setStatus({ state: FIELD.OK,      message: okMessage });
      else                     setStatus({ state: FIELD.TAKEN,   message: data.reason || takenMessage });
    } catch {
      // Silent fallback — the server still rejects duplicates on submit.
      setStatus({ state: FIELD.IDLE, message: '' });
      lastChecked.current = '';
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invalidMessage, okMessage, takenMessage]);

  // Debounced check as the user types.
  useEffect(() => {
    clearTimeout(timer.current);
    if (!value) return undefined;
    timer.current = setTimeout(() => run(value), DEBOUNCE_MS);
    return () => clearTimeout(timer.current);
  }, [value, run]);

  useEffect(() => () => clearTimeout(timer.current), []);

  /** onBlur — fire immediately instead of waiting out the debounce. */
  const onBlur = useCallback(() => {
    clearTimeout(timer.current);
    return run(value);
  }, [run, value]);

  /** Force a check before submit, for users who type fast and hit Enter. */
  const verify = useCallback(() => {
    clearTimeout(timer.current);
    return run(value);
  }, [run, value]);

  const reset = useCallback(() => {
    clearTimeout(timer.current);
    lastChecked.current = '';
    setStatus({ state: FIELD.IDLE, message: '' });
  }, []);

  /** Clears the indicator the instant the user edits the field. */
  const clear = useCallback(() => setStatus({ state: FIELD.IDLE, message: '' }), []);

  return {
    state: status.state,
    message: status.message,
    blocksSubmit: [FIELD.CHECKING, FIELD.TAKEN, FIELD.INVALID].includes(status.state),
    onBlur,
    verify,
    reset,
    clear,
  };
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CNIC_RE  = /^\d{13}$/;

export const useEmailAvailability = (value) => useAvailabilityCheck({
  value,
  check: checkEmail,
  normalize: (v) => (v ?? '').trim().toLowerCase(),
  pattern: EMAIL_RE,
  invalidMessage: 'Invalid email format.',
  okMessage: 'Email is available.',
  takenMessage: 'Email already registered.',
});

export const useCnicAvailability = (value) => useAvailabilityCheck({
  value,
  check: checkCnic,
  normalize: (v) => (v ?? '').replace(/[-\s]/g, ''),
  pattern: CNIC_RE,
  invalidMessage: 'CNIC must be exactly 13 digits.',
  okMessage: 'CNIC is available.',
  takenMessage: 'CNIC already registered.',
});
