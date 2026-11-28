import { regulate, type Ecosystem, type Job } from "./regulator";

export type SignalKind = "listing.observed" | "evidence.verified" | "evidence.rejected" | "analysis.completed" | "source.failed";
export type Signal = { id: string; kind: SignalKind; subject: string; observedAt: number; expiresAt: number };
export type NervousState = { resources: Ecosystem; seen: Record<string, number>; inbox: Signal[] };
const routes: Record<SignalKind, readonly Job["kind"][]> = {
  "listing.observed": ["archive", "verify"],
  "evidence.verified": ["archive", "analyze"],
  "evidence.rejected": ["archive"],
  "analysis.completed": ["archive"],
  "source.failed": ["archive", "verify"]
};
const priorities: Record<Job["kind"], number> = {archive: 100, verify: 90, collect: 80, analyze: 40};
export function tick(state: NervousState, incoming: readonly Signal[], now: number,
  costs: Readonly<Record<Job["kind"], number>>, maxSignals = 1000) {
  if (!Number.isSafeInteger(maxSignals) || maxSignals < 1 || !Number.isFinite(now) ||
    Object.values(costs).some(v => !Number.isFinite(v) || v <= 0)) throw new Error("invalid policy");
  const seen = new Map(Object.entries(state.seen).filter(([,expiry]) => expiry > now));
  const waiting = new Map<string, Signal>();
  const rejected: string[] = [];
  for (const s of [...state.inbox, ...incoming]) {
    if (!s.id || !s.subject || !Object.hasOwn(routes,s.kind) || !Number.isFinite(s.observedAt) ||
      !Number.isFinite(s.expiresAt) || s.observedAt > now || s.expiresAt <= now || s.expiresAt <= s.observedAt) {
      rejected.push(s.id); continue;
    }
    if (!seen.has(s.id) && !waiting.has(s.id)) waiting.set(s.id,s);
  }
  const jobs: Job[] = [];
  const processed: string[] = [];
  const inbox: Signal[] = [];
  for (const s of waiting.values()) {
    if (seen.size >= maxSignals) { inbox.push(s); continue; }
    seen.set(s.id,s.expiresAt);
    processed.push(s.id);
    for (const kind of routes[s.kind]) jobs.push({id: JSON.stringify([s.id,kind]), kind, cost: costs[kind], priority: priorities[kind], dueAt: now});
  }
  const decision = regulate(state.resources,now,jobs);
  return {state: {resources: decision.state, seen: Object.fromEntries(seen), inbox}, admitted: decision.admitted, deferred: decision.deferred, processed, rejected};
}
