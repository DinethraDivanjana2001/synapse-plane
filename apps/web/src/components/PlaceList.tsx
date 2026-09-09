import type { TravelPlace } from "../lib/taskOutput";

function stars(rating: number): string {
  const full = Math.round(rating);
  return "*".repeat(Math.max(0, Math.min(5, full))) + " " + rating.toFixed(1);
}

// Named attractions within a destination, ranked by rating — the travel
// equivalent of RestaurantRanking, using the same discovery mechanism
// (search + LLM extraction in real mode, curated facts in demo mode) applied
// to landmarks/viewpoints/hikes instead of restaurants.
export function PlaceList({ places }: { places: TravelPlace[] }) {
  if (places.length === 0) return null;

  const sorted = [...places].sort((a, b) => b.rating - a.rating);
  const groups = new Map<string, TravelPlace[]>();
  for (const place of sorted) {
    const key = place.destination ?? "";
    groups.set(key, [...(groups.get(key) ?? []), place]);
  }

  return (
    <div>
      {[...groups.entries()].map(([destination, group]) => (
        <div key={destination || "_"} style={{ marginBottom: 14 }}>
          {destination && (
            <div className="muted" style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>
              Places in {destination}
            </div>
          )}
          <div className="restaurant-list">
            {group.map((place, i) => (
              <div className="restaurant-card" key={`${place.name}-${i}`}>
                <span className="rank-number">#{i + 1}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{place.name}</div>
                  <p className="muted" style={{ fontSize: 12.5, margin: "2px 0 4px" }}>
                    {place.description}
                  </p>
                  <div className="row">
                    <span className="tag">{place.category}</span>
                    <span className="stars">{stars(place.rating)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
