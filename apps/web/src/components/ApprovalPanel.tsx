import { useState } from "react";
import { CalendarStrip } from "./CalendarStrip";
import { CountdownTimer } from "./CountdownTimer";
import { RestaurantRanking } from "./RestaurantRanking";
import { collectCandidates, collectTimeSlots, type TimeSlotOption } from "../lib/taskOutput";
import type { ApprovalDecision, ApprovalProposal, TaskSummary } from "../api/types";

interface Props {
  proposal: ApprovalProposal;
  tasks: TaskSummary[];
  onApprove: (decision: ApprovalDecision) => Promise<void>;
  onReject: () => Promise<void>;
}

// Human-in-the-loop checkpoint for a CONSEQUENTIAL_WRITE task. The user can
// change the restaurant and the time here — nothing is written until Approve.
export function ApprovalPanel({ proposal, tasks, onApprove, onReject }: Props) {
  const [busy, setBusy] = useState(false);

  const candidates = collectCandidates(tasks);
  const slots = collectTimeSlots(tasks);

  const [chosenName, setChosenName] = useState<string>(proposal.restaurant_name);
  const [chosenSlot, setChosenSlot] = useState<TimeSlotOption | null>(null);

  const chosenCandidate = candidates.find((c) => c.name === chosenName);
  const changedRestaurant = chosenName !== proposal.restaurant_name;
  const startTime = chosenSlot?.start_time ?? proposal.start_time;
  const endTime = chosenSlot?.end_time ?? proposal.end_time;

  async function run(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
    }
  }

  function approve() {
    return onApprove({
      selected_restaurant: changedRestaurant && chosenCandidate ? chosenCandidate : undefined,
      selected_start_time: chosenSlot ? chosenSlot.start_time : undefined,
      selected_end_time: chosenSlot ? chosenSlot.end_time : undefined,
    });
  }

  const start = new Date(startTime);
  const end = new Date(endTime);
  const dateLabel = start.toLocaleDateString(undefined, {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
  const timeLabel = `${start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} - ${end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;

  const address =
    (changedRestaurant && typeof chosenCandidate?.address === "string"
      ? chosenCandidate.address
      : proposal.address) || "";

  return (
    <div className="approval-panel">
      <div className="approval-heading">
        <h3 style={{ margin: 0 }}>Approval Required</h3>
        <CountdownTimer expiresAt={proposal.expires_at} />
      </div>
      <p className="muted">Nothing is added to your calendar until you approve.</p>

      {candidates.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div className="section-title">Choose a restaurant ({candidates.length} found)</div>
          <RestaurantRanking
            candidates={candidates}
            selectedName={chosenName}
            onSelect={(c) => {
              if (typeof c.name === "string") setChosenName(c.name);
            }}
          />
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <div className="section-title">Choose a time</div>
        <CalendarStrip slots={slots} selectedStart={startTime} onSelect={setChosenSlot} />
      </div>

      <div className="card" style={{ background: "var(--surface)" }}>
        <div className="muted" style={{ marginBottom: 4 }}>
          Proposed action
        </div>
        <strong>{chosenName}</strong>
        {address && <div className="muted">{address}</div>}
        <div style={{ marginTop: 6 }}>
          {dateLabel}, {timeLabel} ({proposal.timezone})
        </div>
        <div className="muted" style={{ marginTop: 6 }}>
          Calendar: {proposal.calendar_id}
        </div>
      </div>

      <div className="security-hash mono" style={{ marginTop: 10 }}>
        Verification: {(proposal.action_digest ?? proposal.proposal_id).slice(0, 16)}...
      </div>

      <div className="row" style={{ marginTop: 16 }}>
        <button className="btn btn-approve" disabled={busy} onClick={() => run(approve)}>
          Approve
        </button>
        <button className="btn btn-reject" disabled={busy} onClick={() => run(onReject)}>
          Reject
        </button>
      </div>
    </div>
  );
}
