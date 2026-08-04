/**
 * Page title + subtitle, with an optional right-aligned action.
 *
 * Renders the exact two shapes the pages used by hand: a flex row when there
 * is an action button, and a plain title/subtitle pair when there isn't.
 */
export default function PageHeader({ title, subtitle, action }) {
  if (!action) {
    return (
      <>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-sub">{subtitle}</p>}
      </>
    );
  }

  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-sub m-0">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
