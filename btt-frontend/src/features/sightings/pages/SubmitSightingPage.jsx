import { useEffect, useRef, useState } from 'react';
import { useList } from '@/shared/hooks/useFetch';
import { getSightings } from '../api';
import SightingForm from '../components/SightingForm';
import ConfidenceScore from '../components/ConfidenceScore';
import PageHeader from '@/shared/components/layout/PageHeader';
import { Alert, Badge, Spinner, EmptyState } from '@/shared/components/ui';
import { formatDate } from '@/shared/lib/formatters';

const SUCCESS_MS = 6000;

export default function SubmitSightingPage() {
  const [success, setSuccess] = useState(false);
  const successTimer = useRef(null);
  const { items: sightings, loading, refetch } = useList(getSightings, []);

  useEffect(() => () => clearTimeout(successTimer.current), []);

  function handleSuccess() {
    setSuccess(true);
    clearTimeout(successTimer.current);
    successTimer.current = setTimeout(() => setSuccess(false), SUCCESS_MS);
    refetch();   // refresh the history table immediately
  }

  return (
    <div>
      <PageHeader
        title="Submit a Sighting"
        subtitle="Report a suspicious bike to help recover stolen property."
      />

      {success && (
        <Alert
          type="success"
          message="Sighting submitted! Fuzzy-match analysis ran automatically. Authorities will be notified if a strong match is found."
        />
      )}

      <div className="card max-w-xl mb-8">
        <SightingForm onSuccess={handleSuccess} />
      </div>

      {/* ── My Sightings history ─────────────────────────────────────────── */}
      <h2 className="font-heading text-base font-semibold text-gray-100 mb-3">My Sightings</h2>

      {loading ? <Spinner /> : sightings.length === 0 ? (
        <div className="card max-w-2xl">
          <EmptyState
            icon="👁️"
            title="No sightings submitted yet"
            subtitle="Your submitted sightings will appear here so you can track their status."
          />
        </div>
      ) : (
        <div className="card p-0 overflow-hidden max-w-4xl">
          <table className="tbl">
            <thead className="bg-btt-700">
              <tr>
                <th>ID</th>
                <th>Partial Numbers</th>
                <th>Confidence</th>
                <th>City</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {sightings.map((s) => (
                <tr key={s.id}>
                  <td><span className="mono text-primary">#{s.id}</span></td>
                  <td>
                    {s.raw_engine_number  && <div className="mono text-[11px]">Eng: {s.raw_engine_number}</div>}
                    {s.raw_chassis_number && <div className="mono text-[11px]">Chs: {s.raw_chassis_number}</div>}
                  </td>
                  <td><ConfidenceScore score={s.fuzzy_match_score} /></td>
                  <td className="text-muted">{s.sighting_city ?? '—'}</td>
                  <td>
                    <Badge variant={s.is_verified ? 'green' : 'amber'}>
                      {s.is_verified ? 'Verified' : 'Pending'}
                    </Badge>
                  </td>
                  <td className="text-faint text-xs">{formatDate(s.sighting_date ?? s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
