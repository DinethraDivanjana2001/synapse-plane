import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createExecution, getProfile } from "../api/client";
import type { UserProfile } from "../api/types";

const DEMO_USER_ID = "user-dinethra";

const SCENARIOS = {
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
} as const;

type ScenarioKey = keyof typeof SCENARIOS;

export function IntentSubmission() {
  const navigate = useNavigate();
  const [scenario, setScenario] = useState<ScenarioKey>("normal");
  const [intent, setIntent] = useState<string>(SCENARIOS.normal.intent);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProfile(DEMO_USER_ID)
      .then(setProfile)
      .catch(() => setProfile(null));
  }, []);

  function selectScenario(key: ScenarioKey) {
    setScenario(key);
    setIntent(SCENARIOS[key].intent);
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const execution = await createExecution(intent, SCENARIOS[scenario].injectFailure);
      navigate(`/executions/${execution.execution_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="card">
        <h2>What would you like to do?</h2>
        <label className="field-label">Intent</label>
        <textarea value={intent} onChange={(e) => setIntent(e.target.value)} />

        <label className="field-label" style={{ marginTop: 14 }}>
          Demo scenario
        </label>
        <div className="scenario-selector">
          {(Object.keys(SCENARIOS) as ScenarioKey[]).map((key) => (
            <button
              key={key}
              className={`btn${scenario === key ? " selected" : ""}`}
              onClick={() => selectScenario(key)}
            >
              {SCENARIOS[key].label}
            </button>
          ))}
        </div>

        {error && (
          <p className="muted" style={{ color: "var(--red)", marginTop: 10 }}>
            {error}
          </p>
        )}

        <button
          className="btn btn-primary"
          style={{ marginTop: 16 }}
          disabled={submitting || intent.trim().length === 0}
          onClick={submit}
        >
          {submitting ? "Submitting…" : "Submit"}
        </button>
      </div>

      {profile && (
        <div className="card">
          <h3>{profile.display_name}</h3>
          <div className="pref-grid">
            <div>
              <div className="muted">Location</div>
              {profile.home_location.label}
            </div>
            <div>
              <div className="muted">Timezone</div>
              {profile.timezone}
            </div>
            <div>
              <div className="muted">Preferred dinner time</div>
              {profile.food_preferences.preferred_dinner_time}
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            {profile.food_preferences.cuisines.map((c) => (
              <span className="tag" key={c}>
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
