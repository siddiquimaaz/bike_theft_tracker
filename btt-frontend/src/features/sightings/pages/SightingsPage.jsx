import { useCallback, useRef, useState } from 'react';
import { useList } from '@/shared/hooks/useFetch';
import { getSightings, verifySighting } from '../api';
import { getStolenBikes } from '@/features/bikes/api';
import ConfidenceScore from '../components/ConfidenceScore';
import PageHeader from '@/shared/components/layout/PageHeader';
import DetailList from '@/shared/components/data/DetailList';
import { Alert, Badge, Button, Modal, Spinner, EmptyState } from '@/shared/components/ui';
import { unwrapList, apiErrorMessage } from '@/shared/lib/http';
import { formatDate } from '@/shared/lib/formatters';

export default function SightingsPage() {
  const { items: sightings, loading, refetch } = useList(getSightings, []);

  const [stolenBikes,  setStolenBikes]  = useState([]);
  const [detail,       setDetail]       = useState(null);
  const [verifying,    setVerifying]    = useState(false);
  const [selectedBike, setSelectedBike] = useState('');
  const [error,        setError]        = useState('');

  // The dropdown is only rendered inside the detail modal, so the stolen-bike
  // list is fetched the first time a row is opened rather than on page load.
  const stolenBikesLoaded = useRef(false);

  const loadStolenBikes = useCallback(async () => {
    if (stolenBikesLoaded.current) return;
    stolenBikesLoaded.current = true;
    try {
      const { data } = await getStolenBikes();
      setStolenBikes(unwrapList(data));
    } catch {
      stolenBikesLoaded.current = false; // allow a retry on the next open
    }
  }, []);

  function openDetail(s) {
    setDetail(s);
    setError('');
    // Pre-select the fuzzy-matched bike if one exists
    setSelectedBike(s.top_match_info?.bike_id ? String(s.top_match_info.bike_id) : '');
    loadStolenBikes();
  }

  function closeDetail() {
    setDetail(null);
    setSelectedBike('');
    setError('');
  }

  async function verify(sighting) {
    const bikeId = selectedBike ? parseInt(selectedBike, 10) : sighting.top_match_info?.bike_id;
    if (!bikeId) {
      setError('Select or enter the matched bike to verify this sighting.');
      return;
    }
    setVerifying(true);
    setError('');
    try {
      await verifySighting(sighting.id, bikeId);
      refetch();
      closeDetail();
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to verify sighting.'));
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Sightings"
        subtitle="Community-reported bike sightings awaiting verification"
      />

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
                  {sightings.map((s) => (
                    <tr key={s.id} className="cursor-pointer" onClick={() => openDetail(s)}>
                      <td><span className="mono text-primary">#{s.id}</span></td>
                      <td>
                        {s.raw_engine_number  && <div className="mono text-[11px]">Eng: {s.raw_engine_number}</div>}
                        {s.raw_chassis_number && <div className="mono text-[11px]">Chs: {s.raw_chassis_number}</div>}
                      </td>
                      <td><ConfidenceScore score={s.fuzzy_match_score} /></td>
                      <td className="text-muted">{s.sighting_city ?? '—'}</td>
                      <td>
                        <Badge variant={s.is_verified ? 'green' : 'amber'}>{s.is_verified ? 'Verified' : 'Pending'}</Badge>
                      </td>
                      <td className="text-faint text-xs">{formatDate(s.sighting_date ?? s.created_at)}</td>
                      <td onClick={(e) => e.stopPropagation()}>
                        {!s.is_verified && (
                          <Button variant="green" size="sm" onClick={() => openDetail(s)}>Verify</Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}

      {detail && (
        <Modal title={`Sighting #${detail.id}`} onClose={closeDetail}>
          <div className="flex gap-2 flex-wrap items-center mb-4">
            <Badge variant={detail.is_verified ? 'green' : 'amber'}>{detail.is_verified ? 'Verified' : 'Pending'}</Badge>
            <ConfidenceScore score={detail.fuzzy_match_score} scoreFormat="dash" />
          </div>

          <DetailList
            className="mb-4"
            labelWidth="w-36"
            valueClassName="mono"
            rows={[
              ['Engine (partial)',  detail.raw_engine_number],
              ['Chassis (partial)', detail.raw_chassis_number],
              ['City',              detail.sighting_city],
              ['Description',       detail.sighting_description],
            ]}
          />

          <Alert type="error" message={error} onClose={() => setError('')} />

          {!detail.is_verified && (
            <div>
              <div className="form-row">
                <label>Link to Stolen Bike *</label>
                <select value={selectedBike} onChange={(e) => setSelectedBike(e.target.value)}>
                  <option value="">— Select stolen bike —</option>
                  {/* Pre-selected fuzzy match shown first */}
                  {detail.top_match_info && (
                    <option value={String(detail.top_match_info.bike_id)}>
                      ✓ AI Match — #{detail.top_match_info.bike_id} {detail.top_match_info.make} {detail.top_match_info.model} ({Math.round(detail.fuzzy_match_score ?? 0)}% confidence)
                    </option>
                  )}
                  {stolenBikes
                    .filter((b) => !detail.top_match_info || b.id !== detail.top_match_info.bike_id)
                    .map((b) => (
                      <option key={b.id} value={String(b.id)}>
                        #{b.id} {b.make} {b.model} — {b.engine_number}
                      </option>
                    ))
                  }
                </select>
                {stolenBikes.length === 0 && (
                  <p className="text-xs text-muted mt-1">No stolen bikes found in system.</p>
                )}
              </div>
              <Button variant="green" loading={verifying} onClick={() => verify(detail)}>
                ✓ Verify &amp; Notify Owner
              </Button>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}
