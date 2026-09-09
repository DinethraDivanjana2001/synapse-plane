import { useState } from "react";
import { StatusBadge } from "./StatusBadge";
import { usedFallback } from "../lib/taskOutput";
import type { TaskSummary } from "../api/types";

// One node in the DAG flow — a task box with status, agent, and optional
// fallback indicator derived from real candidate.source data.
export function TaskCard({ task }: { task: TaskSummary }) {
  const [expanded, setExpanded] = useState(false);
  // source: "places_fallback_tool" only ever comes from the demo-mode fallback
  // tool (see demo/agents.py) — not tied to any particular task_id, since
  // real-mode plans name this task differently every time.
  const showsFallback = usedFallback(task.output);

  return (
    <div className={`dag-node status-${task.status.toLowerCase()}`}>
      {showsFallback && <div className="fallback-badge">Recovered via fallback</div>}
      <div className="task-name">{task.task_id}</div>
      {task.selected_agent_id && <div className="agent-name">{task.selected_agent_id}</div>}
      <StatusBadge status={task.status} />
      {task.output && (
        <div style={{ marginTop: 8 }}>
          <button className="expand-btn" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "hide output" : "show output"}
          </button>
          {expanded && <pre className="output-json">{JSON.stringify(task.output, null, 2)}</pre>}
        </div>
      )}
    </div>
  );
}
