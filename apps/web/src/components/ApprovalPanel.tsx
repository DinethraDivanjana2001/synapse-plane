import { useState } from "react";
import type { ApprovalProposal } from "../api/types";

interface Props {
  proposal: ApprovalProposal;
  onApprove: () => Promise<void>;
  onReject: () => Promise<void>;
}

// Human-in-the-loop checkpoint for a CONSEQUENTIAL_WRITE task — deliberately
// styled as an action card, not a chat bubble (see step_07 design guidelines).
export function ApprovalPanel({ proposal, onApprove, onReject }: Props) {
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
    }
  }

  const start = new Date(proposal.start_time);
  const end = new Date(proposal.end_time);

  return (
    <div className="approval-panel">
      <h3 style={{ marginTop: 0 }}>Approval Required</h3>
      <p className="muted">{proposal.description}</p>

      <div className="card" style={{ background: "var(--surface-2)" }}>
        <strong>{proposal.restaurant_name}</strong>
        <div className="muted">{proposal.address}</div>
      </div>

      <div className="card" style={{ background: "var(--surface-2)" }}>
        <div className="muted">Proposed calendar event</div>
        <div>
          {start.toLocaleDateString()} · {start.toLocaleTimeString()} →{" "}
          {end.toLocaleTimeString()} ({proposal.timezone})
        </div>
        <div className="muted">Calendar: {proposal.calendar_id}</div>
      </div>

      <div className="row" style={{ marginTop: 14 }}>
        <button
          className="btn btn-approve"
          disabled={busy}
          onClick={() => run(onApprove)}
        >
          ✓ Approve
        </button>
        <button className="btn btn-reject" disabled={busy} onClick={() => run(onReject)}>
          ✗ Reject
        </button>
      </div>
    </div>
  );
}
