import { useState } from 'react';
import { useFetch }      from '../../hooks/useFetch';
import { getSightings }  from '../../api/sightingApi';
import { Badge, Button, Modal, Spinner, EmptyState } from '../../components/UI';
import { formatDate } from '../../utils/formatters';
import API from '../../api/axios';

function confidenceFromScore(score) {
  if (score == null) return null;
  if (score >= 85) return 'HIGH';
  if (score >= 70) return 'MEDIUM';
  return 'LOW';
}

const CONF_COLOR = { HIGH: 'text-emerald-400', MEDIUM: 'text-amber-400', LOW: 'text-red-400' };

export default function SightingsPage() {
  const { data, loading, refetch } = useFetch(getSightings, []);
  const sightings = data?.results ?? data ?? [];
  const [detail,    setDetail]    = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [bikeInput, setBikeInput] = useState('');

  async function verify(sighting) {
    const bikeId = sighting.top_match_info?.bike_id
      ?? (bikeInput ? parseInt(bikeInput) : null);
    if (!bikeId) {
      alert('Enter the matched bike ID to verify.');
      return;
    }
    setVerifying(true);
    try {
      await API.put(`/api/sightings/${sighting.id}/verify/`, { bike_id: bikeId });
      refetch();
      setDetail(null);
      setBikeInput('');
    } catch (err) {
      alert(err.response?.data?.detail ?? err.message);
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Sightings</h1>
      <p className="page-sub">Community-reported bike sightings awaiting verification</p>

      {loading ? <Spinner /> : (
        <div className="card p-0 overflow-hidden">
          {sightings.length === 0
            ? <EmptyState icon="👁️" title="No sightings yet" />
            : (
              <table className="tbl">
                <thead className="bg-btt-700"><tr>
                  <th>ID</th><th>Partial Numbers</th><th>Confidence</th><th>City</th><th>Status</th><th>Date</th><th></th>
                </tr></thead>
                <tbody>
                  {sightings.map((s) => {
                    const conf = confidenceFromScore(s.fuzzy_match_score);
                    return (
                      <tr key={s.id} className="cursor-pointer" onClick={() => { setDetail(s); setBikeInput(''); }}>
                        <td><span className="mono text-primary">#{s.id}</span></td>
                        <td>
                          {s.raw_engine_number  && <div className="mono text-[11px]">Eng: {s.raw_engine_number}</div>}
                          {s.raw_chassis_number && <div className="mono text-[11px]">Chs: {s.raw_chassis_number}</div>}
                        </td>
                        <td>
                          <span className={`mono text-xs font-semibold ${CONF_COLOR[conf] ?? 'text-muted'}`}>
                            {conf ?? '—'} {s.fuzzy_match_score != null ? `(${Math.round(s.fuzzy_match_score)}%)` : ''}
                          </span>
                        </td>
                        <td className="text-muted">{s.sighting_city ?? '—'}</td>
                        <td>
                          <Badge variant={s.is_verified ? 'green' : 'amber'}>{s.is_verified ? 'Verified' : 'Pending'}</Badge>
                        </td>
                        <td className="text-faint text-xs">{formatDate(s.sighting_date ?? s.created_at)}</td>
                        <td onClick={(e) => e.stopPropagation()}>
                          {!s.is_verified && (
                            <Button variant="green" size="sm" onClick={() => { setDetail(s); setBikeInput(''); }}>Verify</Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
        </div>
      )}

      {detail && (
        <Modal title={`Sighting #${detail.id}`} onClose={() => { setDetail(null); setBikeInput(''); }}>
          <div className="flex gap-2 flex-wrap mb-4">
            <Badge variant={detail.is_verified ? 'green' : 'amber'}>{detail.is_verified ? 'Verified' : 'Pending'}</Badge>
            {(() => {
              const conf = confidenceFromScore(detail.fuzzy_match_score);
              return conf ? (
                <span className={`mono text-xs font-semibold ${CONF_COLOR[conf] ?? ''}`}>
                  {conf} {detail.fuzzy_match_score != null ? `— ${Math.round(detail.fuzzy_match_score)}%` : ''}
                </span>
              ) : null;
            })()}
          </div>
          <table className="tbl mb-4">
            <tbody>
              {[
                ['Engine (partial)',  detail.raw_engine_number],
                ['Chassis (partial)', detail.raw_chassis_number],
                ['City',              detail.sighting_city],
                ['Description',       detail.sighting_description],
                ['Top match bike ID', detail.top_match_info?.bike_id],
                ['Match make/model',  detail.top_match_info ? `${detail.top_match_info.make} ${detail.top_match_info.model}` : null],
              ].filter(([, v]) => v).map(([k, v]) => (
                <tr key={k}>
                  <td className="text-faint text-xs w-36 border-none py-1">{k}</td>
                  <td className="text-sm text-gray-100 border-none py-1 mono">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {!detail.is_verified && (
            <div>
              {!detail.top_match_info?.bike_id && (
                <div className="form-row">
                  <label>Matched Bike ID (manual)</label>
                  <input type="number" placeholder="Enter bike ID to link" value={bikeInput} onChange={(e) => setBikeInput(e.target.value)} />
                </div>
              )}
              <Button variant="green" loading={verifying} onClick={() => verify(detail)}>
                ✓ Verify & Notify Owner
              </Button>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}
