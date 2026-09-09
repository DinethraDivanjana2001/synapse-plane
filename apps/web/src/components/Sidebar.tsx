import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getProfile, listAgents } from "../api/client";
import { AgentStatusDot } from "./AgentStatusDot";
import { StatusBadge } from "./StatusBadge";
import { clearHistory, loadHistory, type HistoryEntry } from "../lib/history";
import type { AgentManifest, UserProfile } from "../api/types";

const DEMO_USER_ID = "user-dinethra";

export function Sidebar() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [agents, setAgents] = useState<AgentManifest[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    getProfile(DEMO_USER_ID)
      .then(setProfile)
      .catch(() => setProfile(null));
    listAgents()
      .then(setAgents)
      .catch(() => setAgents([]));
    setHistory(loadHistory().slice(0, 5));

    const onStorage = () => setHistory(loadHistory().slice(0, 5));
    window.addEventListener("storage", onStorage);
    const interval = setInterval(onStorage, 3000);
    return () => {
      window.removeEventListener("storage", onStorage);
      clearInterval(interval);
    };
  }, []);

  return (
    <>
      <div className="brand" style={{ marginBottom: 24 }}>
        <span className="brand-mark" />
        SynapsePlane
      </div>

      {profile && (
        <div className="sidebar-section profile-card">
          <div className="section-title">Profile</div>
          <div className="card">
            <div className="name">{profile.display_name}</div>
            <div className="muted">{profile.home_location.label}</div>
            <div className="muted">{profile.timezone}</div>
            <div className="muted">Dinner: {profile.food_preferences.preferred_dinner_time}</div>
            <div style={{ marginTop: 8 }}>
              {profile.food_preferences.cuisines.map((c) => (
                <span className="tag" key={c}>
                  {c}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="sidebar-section">
        <div className="section-title">Execution history</div>
        {history.length === 0 && <p className="muted">No executions yet.</p>}
        <div className="history-list">
          {history.map((h) => (
            <Link className="history-item" to={`/executions/${h.execution_id}`} key={h.execution_id}>
              <span className="intent">{h.intent_text.slice(0, 30)}</span>
              <StatusBadge status={h.status} />
            </Link>
          ))}
        </div>
        {history.length > 0 && (
          <button
            className="btn"
            style={{ marginTop: 8, fontSize: 12, padding: "6px 12px" }}
            onClick={() => {
              clearHistory();
              setHistory([]);
            }}
          >
            Clear history
          </button>
        )}
      </div>

      <div className="sidebar-section">
        <div className="section-title">Agents online</div>
        {agents.map((a) => (
          <AgentStatusDot agent={a} key={a.agent_id} />
        ))}
      </div>
    </>
  );
}
