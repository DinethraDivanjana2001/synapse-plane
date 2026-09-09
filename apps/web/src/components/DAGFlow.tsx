import { TaskCard } from "./TaskCard";
import type { TaskSummary } from "../api/types";

// Renders tasks left-to-right in creation order (the order the workflow
// definition lists them in, which the API preserves) — the API doesn't
// expose a depends_on graph, so this is an approximation, not a real DAG
// layout.
export function DAGFlow({ tasks }: { tasks: TaskSummary[] }) {
  if (tasks.length === 0) {
    return <p className="muted">No tasks yet.</p>;
  }
  return (
    <div className="dag-flow">
      {tasks.map((t, i) => (
        <div key={t.task_id} style={{ display: "flex", alignItems: "flex-start" }}>
          <TaskCard task={t} />
          {i < tasks.length - 1 && <span className="dag-arrow">&#8594;</span>}
        </div>
      ))}
    </div>
  );
}
