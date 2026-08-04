import { useState, useCallback, useRef } from 'react';

/**
 * Controlled-form state for the small forms in this app.
 *
 * `set('field')` returns a stable-enough change handler, replacing the
 * `const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))`
 * line that was copy-pasted into every form component.
 */
export function useForm(initialValues) {
  const initialRef = useRef(initialValues);
  const [values, setValues] = useState(initialValues);

  const setValue = useCallback((key, value) => {
    setValues((v) => ({ ...v, [key]: value }));
  }, []);

  const set = useCallback((key) => (e) => {
    setValues((v) => ({ ...v, [key]: e?.target ? e.target.value : e }));
  }, []);

  const reset = useCallback((next) => {
    setValues(next ?? initialRef.current);
  }, []);

  return { values, set, setValue, setValues, reset };
}
