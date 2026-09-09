import type { TaskSummary } from "../api/types";

const CANDIDATE_LIST_KEYS = ["candidates", "restaurants", "venues", "results"];

export function findTask(tasks: TaskSummary[], idFragment: string): TaskSummary | undefined {
  return tasks.find((t) => t.task_id.includes(idFragment));
}

export interface TimeSlotOption {
  start_time: string;
  end_time: string;
  is_free: boolean;
}

// Task ids are LLM-generated and differ every run ("discover_places",
// "discover_restaurants", "find_venues"...), so never match on the name —
// find the task by the shape of what it returned.
export function collectCandidates(tasks: TaskSummary[]): Record<string, unknown>[] {
  const seen = new Set<string>();
  const unique: Record<string, unknown>[] = [];
  for (const task of tasks) {
    for (const candidate of extractCandidateList(task.output)) {
      const name = typeof candidate.name === "string" ? candidate.name : JSON.stringify(candidate);
      if (seen.has(name)) continue;
      seen.add(name);
      unique.push(candidate);
    }
  }
  return unique;
}

export function collectTimeSlots(tasks: TaskSummary[]): TimeSlotOption[] {
  for (const task of tasks) {
    const slots = task.output?.slots;
    if (Array.isArray(slots) && slots.length > 0) return slots as TimeSlotOption[];
  }
  return [];
}

// Looks for any known array field in a task's output; falls back to
// treating a single non-array object as one ranked item.
export function extractCandidateList(output: Record<string, unknown> | null): Record<string, unknown>[] {
  if (!output) return [];
  for (const key of CANDIDATE_LIST_KEYS) {
    const value = output[key];
    if (Array.isArray(value)) return value as Record<string, unknown>[];
  }
  if (Object.keys(output).length > 0 && typeof output.name === "string") {
    return [output];
  }
  return [];
}

export interface TravelRecommendation {
  selected_destination: string;
  reasoning: string;
}

// The travel use case's "conclusion" — internal-planning-decision's
// alternatives.compare output. Distinct shape from the restaurant
// recommendation (no "candidates"/"selected" keys), so it's never confused
// with a dining result.
export function findTravelRecommendation(tasks: TaskSummary[]): TravelRecommendation | null {
  for (const task of tasks) {
    const out = task.output;
    if (out && typeof out.selected_destination === "string" && typeof out.reasoning === "string") {
      return { selected_destination: out.selected_destination, reasoning: out.reasoning };
    }
  }
  return null;
}

export interface WeatherForecast {
  location: string;
  condition: string;
  temperature_c: number;
  precipitation_probability: number;
  rain_likely: boolean;
  advisory: string;
}

// A dining weather.check task returns one forecast at the top level; a
// travel weather.check task (no single fixed location to bind) returns a
// "forecasts" dict keyed by destination — both are normalized to a flat list.
export function collectWeatherForecasts(tasks: TaskSummary[]): WeatherForecast[] {
  const results: WeatherForecast[] = [];
  for (const task of tasks) {
    const out = task.output;
    if (!out) continue;
    if (out.available === true && typeof out.condition === "string") {
      results.push(out as unknown as WeatherForecast);
    } else if (out.forecasts && typeof out.forecasts === "object") {
      for (const forecast of Object.values(out.forecasts as Record<string, unknown>)) {
        if (forecast && typeof forecast === "object" && "condition" in forecast) {
          results.push(forecast as WeatherForecast);
        }
      }
    }
  }
  return results;
}

export interface TravelPlace {
  name: string;
  category: string;
  rating: number;
  description: string;
  destination?: string;
}

// research.deep's output carries named attractions two different shapes:
// real mode returns a flat "top_places" array on the task output; demo mode
// nests them per destination under "destinations.<name>.top_places". Both
// are flattened into one list, tagged with which destination each is from.
export function collectTravelPlaces(tasks: TaskSummary[]): TravelPlace[] {
  const places: TravelPlace[] = [];
  for (const task of tasks) {
    const out = task.output;
    if (!out) continue;
    if (Array.isArray(out.top_places)) {
      places.push(...(out.top_places as TravelPlace[]));
    }
    if (out.destinations && typeof out.destinations === "object") {
      for (const [key, raw] of Object.entries(out.destinations as Record<string, unknown>)) {
        const dest = raw as { name?: string; top_places?: TravelPlace[] };
        if (Array.isArray(dest.top_places)) {
          for (const p of dest.top_places) {
            places.push({ ...p, destination: dest.name ?? key });
          }
        }
      }
    }
  }
  return places;
}

// RestaurantCandidate.source is "places_fallback_tool" only when the primary
// places tool failed and the demo agent's internal fallback tool ran instead
// (see demo/agents.py + tools/places_tool.py) — real data, not a guess.
export function usedFallback(output: Record<string, unknown> | null): boolean {
  const candidates = extractCandidateList(output);
  return candidates.some((c) => c.source === "places_fallback_tool");
}
