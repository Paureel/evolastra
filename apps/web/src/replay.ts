export function replayStart(sequence: number | null, latest: number): number {
  if (sequence === null || sequence >= latest) return 1;
  return Math.max(1, sequence);
}

export function advanceReplay(sequence: number, latest: number, rate: number): number {
  return Math.min(Math.max(1, latest), Math.max(1, sequence) + Math.max(1, rate));
}
