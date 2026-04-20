import { useState } from 'react';
import { useFetch }       from '../../hooks/useFetch';
import { getSightings }   from '../../api/sightingApi';
import SightingForm       from '../../components/forms/SightingForm';
import { Alert, Badge, Spinner, EmptyState } from '../../components/UI';
import { formatDate }     from '../../utils/formatters';

function confidenceLabel(score) {
  if (score == null) return null;
  if (score >= 85) return { label: 'HIGH',   color: 'text-emerald-400' };
  if (score >= 70) return { label: 'MEDIUM', color: 'text-amber-400'   };
  return                  { label: 'LOW',    color: 'text-red-400'      };
}

export default function SubmitSightingPage() {
  const [success, setSuccess] = useState(false);
  const { data, loading, refetch } = useFetch(getSightings, []);
  const sightings = data?.results ?? data ?? [];

  function handleSuccess() {
    setSuccess(true);
    setTimeout(() => setSuccess(false), 6000);
    refetch();   // refresh the history table immediately
  }

  return (
    <div>
      <h1 className="page-title">Submit a Sighting</h1>
      <p className="page-sub">Report a suspicious bike to help recover stolen property.</p>

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
              {sightings.map((s) => {
                const conf = confidenceLabel(s.fuzzy_match_score);
                return (
                  <tr key={s.id}>
                    <td><span className="mono text-primary">#{s.id}</span></td>
                    <td>
                      {s.raw_engine_number  && <div className="mono text-[11px]">Eng: {s.raw_engine_number}</div>}
                      {s.raw_chassis_number && <div className="mono text-[11px]">Chs: {s.raw_chassis_number}</div>}
                    </td>
                    <td>
                      {conf ? (
                        <span className={`mono text-xs font-semibold ${conf.color}`}>
                          {conf.label} ({Math.round(s.fuzzy_match_score)}%)
                        </span>
                      ) : <span className="text-muted text-xs">—</span>}
                    </td>
                    <td className="text-muted">{s.sighting_city ?? '—'}</td>
                    <td>
                      <Badge variant={s.is_verified ? 'green' : 'amber'}>
                        {s.is_verified ? 'Verified' : 'Pending'}
                      </Badge>
                    </td>
                    <td className="text-faint text-xs">{formatDate(s.sighting_date ?? s.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
