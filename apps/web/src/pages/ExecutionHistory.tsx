import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { StatusBadge } from "../components/StatusBadge";
import { clearHistory, loadHistory, type HistoryEntry } from "../lib/history";

export function ExecutionHistory() {
  const navigate = useNavigate();
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  if (history.length === 0) {
    return <p className="muted">No executions recorded on this device yet.</p>;
  }

  return (
    <div>
      <div className="spread" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Execution history</h2>
        <button
          className="btn"
          onClick={() => {
            clearHistory();
            setHistory([]);
          }}
        >
          Clear history
        </button>
      </div>
      <table className="history-table">
        <thead>
          <tr>
            <th>Intent</th>
            <th>Scenario</th>
            <th>Status</th>
            <th>Started</th>
          </tr>
        </thead>
        <tbody>
          {history.map((h) => (
            <tr key={h.execution_id} onClick={() => navigate(`/executions/${h.execution_id}`)}>
              <td>{h.intent_text.slice(0, 60)}</td>
              <td className="muted">{h.scenario}</td>
              <td>
                <StatusBadge status={h.status} />
              </td>
              <td className="muted">{new Date(h.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
