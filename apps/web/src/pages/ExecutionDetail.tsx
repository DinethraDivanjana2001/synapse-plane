import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { approveAction, getEvents, getExecution, rejectAction } from "../api/client";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { DAGFlow } from "../components/DAGFlow";
import { EventTimeline } from "../components/EventTimeline";
import { RestaurantRanking } from "../components/RestaurantRanking";
import { StatusBadge } from "../components/StatusBadge";
import { TravelRecommendation } from "../components/TravelRecommendation";
import { WeatherBadge } from "../components/WeatherIcon";
import { updateHistoryStatus } from "../lib/history";
import {
  collectCandidates,
  collectTravelPlaces,
  collectWeatherForecasts,
  findTravelRecommendation,
} from "../lib/taskOutput";
import type { EventSummary, ExecutionDetail as ExecutionDetailT } from "../api/types";

// Statuses where nothing changes without external action (a human decision,
// or the terminal outcome itself) — polling stops here.
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
      updateHistoryStatus(id, d.status);
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
    return <p className="muted">Loading...</p>;
  }

  return (
    <div>
      {/* Section A — header */}
      <div className="card">
        <div className="spread">
          <div>
            <div className="muted mono">{detail.execution_id.slice(0, 8)}</div>
            <StatusBadge status={detail.status} />
          </div>
          <Link to="/">Back / New Intent</Link>
        </div>
        <p style={{ marginBottom: 0, marginTop: 10 }}>{detail.intent_text}</p>
      </div>

      {detail.error &&
        (() => {
          const isUnsupported = detail.error.error_code === "UNSUPPORTED_CAPABILITY";
          return (
            <div className={isUnsupported ? "notice-panel" : "error-panel"}>
              <strong style={{ color: isUnsupported ? "var(--amber)" : "var(--red)" }}>
                {isUnsupported ? "Outside what this system can do" : detail.error.error_code}
              </strong>
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
          );
        })()}

      {/* Section B — task pipeline */}
      {detail.tasks.length > 0 && (
        <div className="card">
          <div className="section-title">Task pipeline</div>
          <DAGFlow tasks={detail.tasks} />
        </div>
      )}

      {/* Travel recommendation — the "conclusion" of the travel use case
          (internal-planning-decision's alternatives.compare output). Was
          previously not rendered anywhere; only visible via "show output". */}
      {(() => {
        const recommendation = findTravelRecommendation(detail.tasks);
        if (!recommendation) return null;
        const forecasts = collectWeatherForecasts(detail.tasks);
        const places = collectTravelPlaces(detail.tasks);
        return (
          <div className="card">
            <div className="section-title">Travel recommendation</div>
            <TravelRecommendation recommendation={recommendation} forecasts={forecasts} places={places} />
          </div>
        );
      })()}

      {/* Weather, standalone — dining's weather.check is informational only
          (doesn't change which restaurant gets picked, see docs/SEED_DATA.md
          test #17), so it has no recommendation panel to live inside. Only
          shown here when there wasn't already a travel recommendation above
          that displays weather itself. */}
      {!findTravelRecommendation(detail.tasks) &&
        (() => {
          const forecasts = collectWeatherForecasts(detail.tasks);
          if (forecasts.length === 0) return null;
          return (
            <div className="card">
              <div className="section-title">Weather</div>
              <div className="weather-row">
                {forecasts.map((f) => (
                  <WeatherBadge key={f.location} forecast={f} />
                ))}
              </div>
            </div>
          );
        })()}

      {/* Discovered options — shown whenever a task found candidates and
          there's no approval step already showing them (a plan can discover
          restaurants without ever creating a calendar event, e.g. "what are
          my choices" with no explicit booking request) */}
      {!detail.pending_approval &&
        (() => {
          const candidates = collectCandidates(detail.tasks);
          if (candidates.length === 0) return null;
          return (
            <div className="card">
              <div className="section-title">Discovered options ({candidates.length})</div>
              <RestaurantRanking candidates={candidates} />
            </div>
          );
        })()}

      {/* Section C — approval */}
      {detail.pending_approval && (
        <ApprovalPanel
          proposal={detail.pending_approval}
          tasks={detail.tasks}
          onApprove={async (decision) => {
            await approveAction(
              detail.execution_id,
              detail.pending_approval!.proposal_id,
              decision
            );
            await refresh();
          }}
          onReject={async () => {
            await rejectAction(detail.execution_id, detail.pending_approval!.proposal_id);
            await refresh();
          }}
        />
      )}

      {/* Section D — event timeline */}
      <div className="card">
        <div className="section-title">Event timeline</div>
        <EventTimeline events={events} />
      </div>
    </div>
  );
}
