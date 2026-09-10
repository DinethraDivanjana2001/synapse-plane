import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createExecution } from "../api/client";
import { addHistoryEntry } from "../lib/history";

// Demo-harness-style "Inject Failure" / "Unsupported Intent" buttons were
// removed — a real product doesn't ship buttons for breaking itself.
// Unsupported requests are tested the same way a real user would hit one:
// just type it (see the guidance panel below).
const STARTER_EXAMPLE = "Find a nice restaurant for dinner with Maya tonight and add it to my calendar";

// What the system can actually do differently depending on exact phrasing —
// shown so the user knows what to mention, not left to guess.
const GUIDANCE: { title: string; hint: string; example: string }[] = [
  {
    title: "Just want suggestions?",
    hint: "Ask a plain question — nothing gets booked, you just get a ranked list.",
    example: "What quiet Italian restaurants are near me tonight?",
  },
  {
    title: "Want it scheduled?",
    hint: "Say so explicitly (\"add it to my calendar\", \"book it\") — otherwise nothing is added.",
    example: "Find a quiet restaurant for dinner with Maya tonight and add it to my calendar",
  },
  {
    title: "Care about the weather?",
    hint: "Mention it directly — it isn't checked unless you ask.",
    example: "Suggest an outdoor dinner spot tonight, check the weather first",
  },
  {
    title: "Breakfast or lunch, not dinner?",
    hint: "Name the meal and the day (\"tomorrow\", \"this Friday\") — both change the time slots shown.",
    example: "Book breakfast with Sithma this Friday",
  },
  {
    title: "Comparing travel destinations?",
    hint: "Name both places — add \"check the weather\" to factor rain into the recommendation.",
    example: "Should I go to Kandy or Galle next month? Compare them and check the weather",
  },
];

export function IntentSubmission() {
  const navigate = useNavigate();
  const [intent, setIntent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function useExample(example: string) {
    setIntent(example);
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const execution = await createExecution(intent, false);
      addHistoryEntry({
        execution_id: execution.execution_id,
        intent_text: intent,
        status: execution.status,
        scenario: "custom",
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
        placeholder={`e.g. "${STARTER_EXAMPLE}"`}
        value={intent}
        onChange={(e) => setIntent(e.target.value)}
      />

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

      <div className="guidance-panel">
        <div className="section-title">What you can ask — and what changes the result</div>
        <div className="guidance-grid">
          {GUIDANCE.map((g) => (
            <div className="guidance-item" key={g.title}>
              <div className="guidance-title">{g.title}</div>
              <p className="muted guidance-hint">{g.hint}</p>
              <button className="guidance-example" onClick={() => useExample(g.example)}>
                &ldquo;{g.example}&rdquo;
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
