import { PlaceList } from "./PlaceList";
import { WeatherBadge } from "./WeatherIcon";
import type {
  TravelPlace,
  TravelRecommendation as TravelRecommendationT,
  WeatherForecast,
} from "../lib/taskOutput";

interface Props {
  recommendation: TravelRecommendationT;
  forecasts: WeatherForecast[];
  places: TravelPlace[];
}

// The travel use case's conclusion — previously nowhere visible in the UI;
// the pipeline ran and succeeded but nothing surfaced the actual answer.
export function TravelRecommendation({ recommendation, forecasts, places }: Props) {
  return (
    <div className="travel-recommendation">
      <div className="travel-recommendation-label">Recommended destination</div>
      <div className="travel-recommendation-name">{recommendation.selected_destination}</div>
      <p className="travel-recommendation-reasoning">{recommendation.reasoning}</p>

      {forecasts.length > 0 && (
        <div className="weather-row">
          {forecasts.map((f) => (
            <WeatherBadge key={f.location} forecast={f} />
          ))}
        </div>
      )}

      {places.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <PlaceList places={places} />
        </div>
      )}
    </div>
  );
}
