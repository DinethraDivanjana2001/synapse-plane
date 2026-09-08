import { useState } from "react";
import { StatusBadge } from "./StatusBadge";
import type { TaskSummary } from "../api/types";

export function TaskCard({ task }: { task: TaskSummary }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="card">
      <div className="spread">
        <div>
          <strong>{task.task_id}</strong>
          {task.selected_agent_id && (
            <div className="muted">agent: {task.selected_agent_id}</div>
          )}
        </div>
        <StatusBadge status={task.status} />
      </div>
      {task.output && (
        <div style={{ marginTop: 10 }}>
          <button className="btn" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "▲ Hide output" : "▼ Show output"}
          </button>
          {expanded && <pre className="output-json">{JSON.stringify(task.output, null, 2)}</pre>}
        </div>
      )}
    </div>
  );
}
