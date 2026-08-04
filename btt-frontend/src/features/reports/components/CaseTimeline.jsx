import { formatDateTime } from '@/shared/lib/formatters';

export default function CaseTimeline({ events = [] }) {
  if (!events.length) {
    return <p className="text-faint text-xs">No timeline events yet.</p>;
  }

  return (
    <div className="mt-4 border border-white/10 rounded-md p-3">
      <h4 className="text-sm font-semibold mb-2">Case Timeline</h4>
      <div className="flex flex-col gap-2">
        {events.map((event) => (
          <div key={event.id} className="text-xs text-gray-300">
            <span className="font-medium text-gray-100">{event.action}</span>
            {' · '}
            {formatDateTime(event.created_at)}
            {event.actor_name ? ` · ${event.actor_name}` : ''}
          </div>
        ))}
      </div>
    </div>
  );
}
