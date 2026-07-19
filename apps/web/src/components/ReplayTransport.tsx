interface ReplayTransportProps {
  compact?: boolean;
  playing: boolean;
  sequence: number | null;
  latestSequence: number;
  status: string;
  unitLabel: "Event" | "Phase";
  rangeLabel: string;
  onToggle: () => void;
  onLive: () => void;
  onSequenceChange: (sequence: number) => void;
}

export function ReplayTransport({
  compact = false,
  playing,
  sequence,
  latestSequence,
  status,
  unitLabel,
  rangeLabel,
  onToggle,
  onLive,
  onSequenceChange,
}: ReplayTransportProps) {
  const actionLabel = playing ? "Pause replay" : sequence === null ? "Replay from beginning" : "Play replay";
  const actionText = playing ? "Pause" : sequence === null ? "Replay" : "Play";

  return (
    <>
      <div className={`timeline-actions${compact ? " compact-timeline-actions" : ""}`}>
        <button className={`replay-button${playing ? " playing" : ""}`} onClick={onToggle} aria-pressed={playing} aria-label={actionLabel}>
          <span aria-hidden="true">{playing ? "Ⅱ" : sequence === null ? "↻" : "▶"}</span>{actionText}
        </button>
        <button className="quiet-button live-button" onClick={onLive} disabled={sequence === null}>Live</button>
      </div>
      <label className={`timeline-range${compact ? " compact-timeline-range" : ""}`}>
        <output aria-live="polite">{status}</output>
        <input
          type="range"
          min={1}
          max={latestSequence}
          value={sequence ?? latestSequence}
          onChange={(event) => onSequenceChange(Number(event.target.value))}
          aria-label={rangeLabel}
        />
        <small>{unitLabel} 1</small><small>{unitLabel} {latestSequence}</small>
      </label>
    </>
  );
}
