import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createExecution } from "../api/client";
import { addHistoryEntry, type ScenarioKey } from "../lib/history";

const SCENARIOS: Record<Exclude<ScenarioKey, "custom">, { label: string; intent: string; injectFailure: boolean }> = {
  normal: {
    label: "Normal",
    intent: "Find a nice restaurant for dinner with Maya tonight and add it to my calendar",
    injectFailure: false,
  },
  failure: {
    label: "Inject Failure",
    intent: "Find a nice restaurant for dinner with Maya tonight and add it to my calendar",
    injectFailure: true,
  },
  unsupported: {
    label: "Unsupported Intent",
    intent: "Buy me the cheapest flight to Singapore",
    injectFailure: false,
  },
};

export function IntentSubmission() {
  const navigate = useNavigate();
  const [intent, setIntent] = useState("");
  const [preferredTime, setPreferredTime] = useState("");
  const [injectFailure, setInjectFailure] = useState(false);
  const [activeScenario, setActiveScenario] = useState<ScenarioKey | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function selectScenario(key: Exclude<ScenarioKey, "custom">) {
    setActiveScenario(key);
    setIntent(SCENARIOS[key].intent);
    setInjectFailure(SCENARIOS[key].injectFailure);
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const execution = await createExecution(intent, injectFailure, preferredTime);
      addHistoryEntry({
        execution_id: execution.execution_id,
        intent_text: intent,
        status: execution.status,
        scenario: activeScenario ?? "custom",
        created_at: new Date().toISOString(),
      });
      navigate(`/executions/${execution.execution_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ padding: 24 }}>
      <h2 style={{ marginTop: 0 }}>What would you like to do?</h2>
      <textarea
        placeholder="e.g. Find a nice Italian restaurant for dinner and add it to my calendar..."
        value={intent}
        onChange={(e) => {
          setIntent(e.target.value);
          setActiveScenario(null);
        }}
      />

      <div style={{ marginTop: 14 }}>
        <label className="field-label" htmlFor="preferred-time">
          Preferred time (optional) &mdash; the system books the closest free slot
        </label>
        <select
          id="preferred-time"
          value={preferredTime}
          onChange={(e) => setPreferredTime(e.target.value)}
          style={{ maxWidth: 260 }}
        >
          <option value="">No preference &mdash; pick the first free slot</option>
          <option value="17:00">5:00 PM</option>
          <option value="18:00">6:00 PM</option>
          <option value="19:00">7:00 PM</option>
          <option value="20:00">8:00 PM</option>
          <option value="21:00">9:00 PM</option>
        </select>
      </div>

      <div className="scenario-chips" style={{ marginTop: 14 }}>
        {(Object.keys(SCENARIOS) as (keyof typeof SCENARIOS)[]).map((key) => (
          <button
            key={key}
            className={`chip${activeScenario === key ? " selected" : ""}`}
            onClick={() => selectScenario(key)}
          >
            {SCENARIOS[key].label}
          </button>
        ))}
      </div>

      {error && (
        <p className="muted" style={{ color: "var(--red)", marginTop: 12 }}>
          {error}
        </p>
      )}

      <button
        className="btn btn-glow"
        style={{ marginTop: 20 }}
        disabled={submitting || intent.trim().length === 0}
        onClick={submit}
      >
        {submitting ? "Executing..." : "Execute Intent"}
      </button>
    </div>
  );
}
