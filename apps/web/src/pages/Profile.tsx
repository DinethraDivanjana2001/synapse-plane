import { useEffect, useState } from "react";
import { getProfile } from "../api/client";
import type { UserProfile } from "../api/types";

const DEMO_USER_ID = "user-dinethra";

// The one thing every recommendation must respect, surfaced on its own —
// not buried in a list of cuisines where it's easy to miss.
function AllergyBanner({ restrictions }: { restrictions: string[] }) {
  if (restrictions.length === 0) return null;
  return (
    <div className="notice-panel" style={{ marginBottom: 20 }}>
      <strong style={{ color: "var(--amber)" }}>Dietary restrictions</strong>
      <p className="muted" style={{ margin: "6px 0 0" }}>
        Every suggestion should respect: {restrictions.map((r) => r.replace(/_/g, " ")).join(", ")}
      </p>
    </div>
  );
}

export function Profile() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProfile(DEMO_USER_ID)
      .then(setProfile)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  if (error) return <p style={{ color: "var(--red)" }}>{error}</p>;
  if (!profile) return <p className="muted">Loading...</p>;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Your profile</h2>
      <p className="muted" style={{ maxWidth: 640 }}>
        This is what the system actually knows about you and uses when planning — not
        decorative. Every recommendation is checked against this.
      </p>

      <AllergyBanner restrictions={profile.food_preferences.dietary_restrictions} />

      <div className="card">
        <div className="section-title">Identity</div>
        <div className="kv">
          <dt>Name</dt>
          <dd>{profile.display_name}</dd>
          <dt>Home</dt>
          <dd>{profile.home_location.label}</dd>
          <dt>Timezone</dt>
          <dd className="mono">{profile.timezone}</dd>
          <dt>Language / currency</dt>
          <dd>
            {profile.language} / {profile.currency}
          </dd>
        </div>
      </div>

      <div className="card">
        <div className="section-title">Food preferences</div>
        <div className="kv">
          <dt>Cuisines</dt>
          <dd>
            {profile.food_preferences.cuisines.map((c) => (
              <span className="tag" key={c}>
                {c}
              </span>
            ))}
          </dd>
          <dt>Dietary restrictions</dt>
          <dd>
            {profile.food_preferences.dietary_restrictions.length > 0 ? (
              profile.food_preferences.dietary_restrictions.map((r) => (
                <span
                  className="tag"
                  key={r}
                  style={{ borderColor: "var(--amber)", color: "var(--amber)" }}
                >
                  {r.replace(/_/g, " ")}
                </span>
              ))
            ) : (
              <span className="muted">None on file</span>
            )}
          </dd>
          <dt>Price level</dt>
          <dd>{profile.food_preferences.price_level}</dd>
          <dt>Max distance</dt>
          <dd>{profile.food_preferences.max_distance_km} km</dd>
          <dt>Preferred dinner time</dt>
          <dd>{profile.food_preferences.preferred_dinner_time}</dd>
        </div>
      </div>

      <div className="card">
        <div className="section-title">Travel preferences</div>
        <div className="kv">
          <dt>Interests</dt>
          <dd>
            {profile.travel_preferences.interests.map((i) => (
              <span className="tag" key={i}>
                {i}
              </span>
            ))}
          </dd>
          <dt>Walking tolerance</dt>
          <dd>{profile.travel_preferences.walking_tolerance}</dd>
          <dt>Pace</dt>
          <dd>{profile.travel_preferences.pace}</dd>
        </div>
      </div>

      <div className="card">
        <div className="section-title">Calendar &amp; approval policy</div>
        <div className="kv">
          <dt>Calendar provider</dt>
          <dd className="mono">{profile.calendar.provider}</dd>
          <dt>Calendar ID</dt>
          <dd className="mono">{profile.calendar.calendar_id}</dd>
          <dt>Approval required for</dt>
          <dd>
            {profile.approval_policy.require_for_external_writes && (
              <span className="tag">external writes</span>
            )}
            {profile.approval_policy.require_for_financial_actions && (
              <span className="tag">financial actions</span>
            )}
          </dd>
        </div>
      </div>

      <p className="muted" style={{ fontSize: 12.5 }}>
        This is the fake seed profile used throughout the demo — see{" "}
        <code>docs/SEED_DATA.md</code> for the full picture, including the 66 memories
        (people, relationships, past visits) that this page doesn't show.
      </p>
    </div>
  );
}
