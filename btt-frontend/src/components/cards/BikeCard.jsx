import Badge from '../UI/Badge';
import Button from '../UI/Button';

export default function BikeCard({ bike, onDelete, onReportStolen }) {
  return (
    <div className="card card-sm card-hover">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-btt bg-btt-600 flex items-center justify-center text-xl flex-shrink-0">🏍</div>
          <div>
            <div className="text-sm font-semibold text-gray-100">{bike.make ?? ''} {bike.model ?? ''}</div>
            <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1">
              <span className="text-[11px] text-muted">Engine: <span className="mono text-gray-300">{bike.engine_number}</span></span>
              <span className="text-[11px] text-muted">Chassis: <span className="mono text-gray-300">{bike.chassis_number}</span></span>
              {bike.plate_number && <span className="text-[11px] text-muted">Plate: <span className="text-gray-300">{bike.plate_number}</span></span>}
              {bike.city         && <span className="text-[11px] text-muted">{bike.city}</span>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Badge variant={bike.is_stolen ? 'red' : 'green'}>{bike.is_stolen ? 'Stolen' : 'Active'}</Badge>
          {/* Only show "Report Stolen" if bike is not already reported stolen */}
          {onReportStolen && !bike.is_stolen && (
            <Button variant="warning" size="sm" onClick={() => onReportStolen(bike)}>
              🚨 Report Stolen
            </Button>
          )}
          {onDelete && <Button variant="danger" size="sm" onClick={() => onDelete(bike.id)}>Remove</Button>}
        </div>
      </div>
    </div>
  );
}
