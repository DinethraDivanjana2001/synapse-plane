import type { WeatherForecast } from "../lib/taskOutput";

// Plain SVG shapes, not emoji — sun for clear/dry, cloud-with-sun for partly
// cloudy, cloud-with-rain for anything wet. Color follows precipitation
// chance, not a fixed palette, so the icon itself carries the signal.
export function WeatherIcon({ forecast, size = 20 }: { forecast: WeatherForecast; size?: number }) {
  const rain = forecast.rain_likely;
  const color = rain ? "var(--blue)" : "var(--amber)";

  if (rain) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-label="rain">
        <path
          d="M7 14a4.5 4.5 0 0 1 .5-8.98A6 6 0 0 1 19 8a4 4 0 0 1-1 7.9H7Z"
          fill={color}
          opacity={0.35}
          stroke={color}
          strokeWidth={1.4}
        />
        <line x1="8" y1="18" x2="7" y2="21" stroke={color} strokeWidth={1.6} strokeLinecap="round" />
        <line x1="12" y1="18" x2="11" y2="21" stroke={color} strokeWidth={1.6} strokeLinecap="round" />
        <line x1="16" y1="18" x2="15" y2="21" stroke={color} strokeWidth={1.6} strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-label="clear">
      <circle cx="12" cy="12" r="5" fill={color} opacity={0.35} stroke={color} strokeWidth={1.4} />
      {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
        <line
          key={deg}
          x1="12"
          y1="2.5"
          x2="12"
          y2="4.5"
          stroke={color}
          strokeWidth={1.6}
          strokeLinecap="round"
          transform={`rotate(${deg} 12 12)`}
        />
      ))}
    </svg>
  );
}

export function WeatherBadge({ forecast }: { forecast: WeatherForecast }) {
  return (
    <div className="weather-badge">
      <WeatherIcon forecast={forecast} />
      <div>
        <div className="weather-badge-location">{forecast.location}</div>
        <div className="weather-badge-detail">
          {forecast.condition}, {Math.round(forecast.temperature_c)}°C ·{" "}
          {forecast.precipitation_probability}% rain
        </div>
      </div>
    </div>
  );
}
