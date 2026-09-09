// Real API shape (RestaurantCandidate, src/synapse_plane/domain/tools.py):
// { name, address, cuisine, rating, price_level, is_quiet, distance_km, source }
export interface Candidate {
  [key: string]: unknown;
}

function stars(rating: number): string {
  const full = Math.round(rating);
  return "*".repeat(Math.max(0, Math.min(5, full))) + " " + rating.toFixed(1);
}

interface Props {
  candidates: Candidate[];
  selectedName?: string;
  onSelect?: (candidate: Candidate) => void;
}

export function RestaurantRanking({ candidates, selectedName, onSelect }: Props) {
  if (candidates.length === 0) {
    return <p className="muted">No venue candidates returned yet.</p>;
  }

  return (
    <div className="restaurant-list">
      {candidates.map((c, i) => {
        const name = typeof c.name === "string" ? c.name : `Candidate ${i + 1}`;
        const address = typeof c.address === "string" ? c.address : null;
        const cuisine = typeof c.cuisine === "string" ? c.cuisine : null;
        const distanceKm = typeof c.distance_km === "number" ? c.distance_km : null;
        const rating = typeof c.rating === "number" ? c.rating : null;
        const isSelected = name === selectedName;

        const selectable = Boolean(onSelect);
        return (
          <div
            className={`restaurant-card${isSelected ? " selected" : ""}${selectable ? " selectable" : ""}`}
            key={`${name}-${i}`}
            onClick={selectable ? () => onSelect!(c) : undefined}
            role={selectable ? "button" : undefined}
            tabIndex={selectable ? 0 : undefined}
            onKeyDown={
              selectable
                ? (e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect!(c);
                    }
                  }
                : undefined
            }
          >
            <span className="rank-number">#{i + 1}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>{name}</div>
              {address && <div className="muted">{address}</div>}
              <div className="row" style={{ marginTop: 4 }}>
                {cuisine && <span className="tag">{cuisine}</span>}
                {distanceKm !== null && <span className="tag">{distanceKm.toFixed(1)} km</span>}
                {rating !== null && <span className="stars">{stars(rating)}</span>}
              </div>
            </div>
            {isSelected && (
              <span className="tag" style={{ borderColor: "var(--green)", color: "var(--green)" }}>
                Selected
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
