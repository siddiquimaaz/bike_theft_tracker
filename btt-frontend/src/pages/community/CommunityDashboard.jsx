import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button, EmptyState, Spinner } from '../../components/UI';
import { useFetch } from '../../hooks/useFetch';
import { getCommunityFeed } from '../../api/reportApi';
import Badge from '../../components/UI/Badge';
import { STATUS_COLORS, STATUS_LABELS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';

export default function CommunityDashboard() {
  const { user }  = useAuth();
  const navigate  = useNavigate();
  const { data: feedData, loading: feedLoading, error: feedError } = useFetch(getCommunityFeed, []);
  const feed = feedData?.results ?? feedData ?? [];

  return (
    <div>
      <h1 className="page-title">Welcome, {user?.full_name?.split(' ')[0] ?? 'there'} 👋</h1>
      <p className="page-sub">You're logged in as a Community Reporter.</p>

      <div className="grid grid-cols-2 gap-4 max-w-2xl">
        <div className="card">
          <div className="text-3xl mb-3">👁️</div>
          <h2 className="font-heading font-semibold text-base text-gray-100 mb-2">Submit a Sighting</h2>
          <p className="text-sm text-muted mb-4 leading-relaxed">
            Spotted a suspicious bike? Even a partial engine or chassis number helps. Our AI fuzzy-matching automatically finds the best stolen bike candidates.
          </p>
          <Button variant="primary" onClick={() => navigate('/community/sightings')}>
            Report a Sighting →
          </Button>
        </div>

        <div className="card">
          <div className="text-3xl mb-3">🔔</div>
          <h2 className="font-heading font-semibold text-base text-gray-100 mb-2">Notifications</h2>
          <p className="text-sm text-muted mb-4 leading-relaxed">
            Get notified when your sighting is verified by authorities and linked to a stolen bike case.
          </p>
          <Button variant="ghost" onClick={() => navigate('/community/notifications')}>
            View Notifications →
          </Button>
        </div>
      </div>

      <div className="mt-5 alert alert-info max-w-2xl">
        <strong>How it works:</strong> Submit a sighting with whatever partial numbers you can read.
        Our RapidFuzz WRatio algorithm scores it against all active stolen bike records.
        Matching sightings are forwarded to the relevant city authority for verification.
      </div>

      <div className="card mt-6 max-w-4xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-heading font-semibold text-base text-gray-100">Same-City Theft Feed</h2>
          <span className="text-xs text-faint">Public case snapshot for community awareness</span>
        </div>

        {feedLoading && <Spinner />}
        {!feedLoading && feedError && (
          <div className="alert alert-warning">
            {feedError || 'Unable to load city theft feed right now.'}
          </div>
        )}
        {!feedLoading && !feedError && feed.length === 0 && (
          <EmptyState
            icon="🏙️"
            title="No active theft cases in your city"
            subtitle="Add your city in profile settings if this looks incorrect."
          />
        )}
        {!feedLoading && !feedError && feed.length > 0 && (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead className="bg-btt-700">
                <tr>
                  <th>Case</th>
                  <th>Bike</th>
                  <th>Status</th>
                  <th>City</th>
                  <th>Theft Date</th>
                </tr>
              </thead>
              <tbody>
                {feed.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="mono text-primary text-xs">{item.reference_number ?? `#${item.id}`}</div>
                      <div className="text-faint text-xs">{item.theft_location_detail ?? 'Location withheld'}</div>
                    </td>
                    <td className="text-sm text-gray-200">
                      {item.bike_info?.make} {item.bike_info?.model}
                      {item.bike_info?.color ? <span className="text-faint"> ({item.bike_info.color})</span> : null}
                    </td>
                    <td>
                      <Badge variant={STATUS_COLORS[item.status] ?? 'gray'}>
                        {STATUS_LABELS[item.status] ?? item.status}
                      </Badge>
                    </td>
                    <td className="text-muted">{item.theft_city ?? '—'}</td>
                    <td className="text-faint text-xs">{formatDate(item.theft_date ?? item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
