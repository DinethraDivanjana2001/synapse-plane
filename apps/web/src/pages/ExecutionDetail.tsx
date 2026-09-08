import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { approveAction, getEvents, getExecution, rejectAction } from "../api/client";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { EventTimeline } from "../components/EventTimeline";
import { StatusBadge } from "../components/StatusBadge";
import { TaskCard } from "../components/TaskCard";
import type { EventSummary, ExecutionDetail as ExecutionDetailT } from "../api/types";

// Statuses where nothing will change without external action (a human
// decision, or the terminal outcome itself) — polling stops here.
const STABLE_STATUSES = new Set([
  "COMPLETED",
  "FAILED",
  "REJECTED",
  "CANCELLED",
  "WAITING_FOR_APPROVAL",
]);

export function ExecutionDetail() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<ExecutionDetailT | null>(null);
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!id) return;
    try {
      const [d, e] = await Promise.all([getExecution(id), getEvents(id)]);
      setDetail(d);
      setEvents(e);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!detail || STABLE_STATUSES.has(detail.status)) return;
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, [detail, refresh]);

  if (error) {
    return <p style={{ color: "var(--red)" }}>{error}</p>;
  }
  if (!detail) {
    return <p className="muted">Loading…</p>;
  }

  return (
    <div>
      <div className="card">
        <div className="spread">
          <div>
            <div className="muted">Execution</div>
            <strong>{detail.execution_id}</strong>
          </div>
          <StatusBadge status={detail.status} />
        </div>
        <p style={{ marginBottom: 0 }}>{detail.intent_text}</p>
      </div>

      {detail.error && (
        <div className="card" style={{ borderColor: "var(--red)" }}>
          <strong style={{ color: "var(--red)" }}>{detail.error.error_code}</strong>
          {detail.error.capabilities && (
            <p className="muted">
              Required capabilities not available: {detail.error.capabilities.join(", ")}
            </p>
          )}
          {detail.error.errors && (
            <ul className="muted">
              {detail.error.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {detail.pending_approval && (
        <ApprovalPanel
          proposal={detail.pending_approval}
          onApprove={async () => {
            await approveAction(detail.execution_id, detail.pending_approval!.proposal_id);
            await refresh();
          }}
          onReject={async () => {
            await rejectAction(detail.execution_id, detail.pending_approval!.proposal_id);
            await refresh();
          }}
        />
      )}

      <h3>Tasks</h3>
      {detail.tasks.map((t) => (
        <TaskCard key={t.task_id} task={t} />
      ))}

      <h3>Event timeline</h3>
      <div className="card">
        <EventTimeline events={events} />
      </div>
    </div>
  );
}
