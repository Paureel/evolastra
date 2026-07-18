export function StatusMark({ status = "unknown", label }: { status?: string; label?: string }) {
  return (
    <span className={`status-mark status-${status}`}>
      <span className="status-glyph" aria-hidden="true" />
      {label ?? status.replaceAll("_", " ")}
    </span>
  );
}
