import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/UI';

export default function CommunityDashboard() {
  const { user }  = useAuth();
  const navigate  = useNavigate();

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
    </div>
  );
}
