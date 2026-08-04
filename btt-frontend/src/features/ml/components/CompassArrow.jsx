/** Compass rose arrow — rendered inline without any extra deps */
export default function CompassArrow({ bearing }) {
  return (
    <span
      style={{ display: 'inline-block', transform: `rotate(${bearing}deg)`, fontSize: '1.25rem', lineHeight: 1 }}
      title={`${bearing}°`}
    >
      ↑
    </span>
  );
}
