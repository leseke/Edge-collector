/** Deterministic resource regulator. Units are caller-defined compute units, not money. */
export type Job = { id: string; kind: "collect" | "verify" | "analyze" | "archive"; cost: number; priority: number; dueAt: number };
export type Ecosystem = { capacity: number; available: number; reserve: number; refillPerMs: number; updatedAt: number; pending: Job[] };
export type Decision = { state: Ecosystem; admitted: Job[]; deferred: Job[] };
const valid = (n: number) => Number.isFinite(n) && n >= 0;
export function regulate(state: Ecosystem, now: number, incoming: readonly Job[] = []): Decision {
  if (![state.capacity,state.available,state.reserve,state.refillPerMs,state.updatedAt,now].every(valid) ||
      state.reserve > state.capacity || state.available > state.capacity || now < state.updatedAt) throw new Error("invalid resource state");
  const jobs = new Map<string, Job>();
  for (const job of [...state.pending,...incoming]) {
    if (!job.id || !valid(job.cost) || job.cost === 0 || !valid(job.priority) || !valid(job.dueAt) ||
        !["collect","verify","analyze","archive"].includes(job.kind)) throw new Error("invalid job");
    if (!jobs.has(job.id)) jobs.set(job.id,job);
  }
  let available = Math.min(state.capacity,state.available+(now-state.updatedAt)*state.refillPerMs);
  const admitted: Job[] = [], deferred: Job[] = [];
  const essential = (j: Job) => j.kind === "collect" || j.kind === "verify" || j.kind === "archive";
  const ordered = [...jobs.values()].sort((a,b)=>Number(essential(b))-Number(essential(a)) || b.priority-a.priority || a.dueAt-b.dueAt || a.id.localeCompare(b.id));
  for (const job of ordered) {
    const floor = essential(job) ? 0 : state.reserve;
    if (job.dueAt <= now && available-job.cost >= floor) { available -= job.cost; admitted.push(job); }
    else deferred.push(job);
  }
  return {state:{...state,available,updatedAt:now,pending:deferred},admitted,deferred};
}
