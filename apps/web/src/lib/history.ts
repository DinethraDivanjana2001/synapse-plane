// Execution history is a pure per-viewer convenience — persisted in
// localStorage only, never sent to or read from the backend.

export type ScenarioKey = "normal" | "failure" | "unsupported" | "custom";

export interface HistoryEntry {
  execution_id: string;
  intent_text: string;
  status: string;
  scenario: ScenarioKey;
  created_at: string;
}

const KEY = "synapseplane.history";
const MAX_ENTRIES = 20;

export function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function addHistoryEntry(entry: HistoryEntry): void {
  try {
    const entries = [entry, ...loadHistory().filter((e) => e.execution_id !== entry.execution_id)];
    localStorage.setItem(KEY, JSON.stringify(entries.slice(0, MAX_ENTRIES)));
  } catch {
    // localStorage unavailable (private mode, blocked) — history just won't persist
  }
}

export function updateHistoryStatus(executionId: string, status: string): void {
  try {
    const entries = loadHistory().map((e) =>
      e.execution_id === executionId ? { ...e, status } : e
    );
    localStorage.setItem(KEY, JSON.stringify(entries));
  } catch {
    // ignore
  }
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
