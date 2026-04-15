import { useState } from 'react';
import SightingForm from '../../components/forms/SightingForm';
import { Alert } from '../../components/UI';

export default function SubmitSightingPage() {
  const [success, setSuccess] = useState(false);

  function handleSuccess() {
    setSuccess(true);
    setTimeout(() => setSuccess(false), 5000);
  }

  return (
    <div>
      <h1 className="page-title">Submit a Sighting</h1>
      <p className="page-sub">Report a suspicious bike to help recover stolen property.</p>

      {success && <Alert type="success" message="Sighting submitted! Fuzzy match analysis is running in the background. Authorities will be notified if a strong match is found." />}

      <div className="card max-w-xl">
        <SightingForm onSuccess={handleSuccess} />
      </div>
    </div>
  );
}
