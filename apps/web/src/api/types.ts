// Mirrors src/synapse_plane/domain models and apps/api response shapes.

export interface AgentManifest {
  agent_id: string;
  name: string;
  ownership: string;
  source_repository: string;
  version: string;
  description: string;
  capabilities: string[];
  implementation_status: string;
  trust_status: string;
  enabled: boolean;
  health_status: string;
  reliability_score: number;
  estimated_latency_ms: number;
  estimated_cost_units: number;
  tags: string[];
}

export interface Location {
  label: string;
  latitude: number;
  longitude: number;
}

export interface FoodPreferences {
  cuisines: string[];
  dietary_restrictions: string[];
  price_level: string;
  max_distance_km: number;
  preferred_dinner_time: string;
}

export interface UserProfile {
  user_id: string;
  display_name: string;
  home_location: Location;
  timezone: string;
  language: string;
  currency: string;
  food_preferences: FoodPreferences;
}

export interface TaskSummary {
  task_id: string;
  status: string;
  selected_agent_id: string | null;
  output: Record<string, unknown> | null;
}

export interface ApprovalProposal {
  proposal_id: string;
  execution_id: string;
  task_id: string;
  restaurant_name: string;
  address: string;
  start_time: string;
  end_time: string;
  timezone: string;
  calendar_id: string;
  description: string;
  status: string;
  expires_at: string;
  action_digest?: string;
}

export interface ExecutionError {
  error_code: string;
  capabilities?: string[];
  errors?: string[];
}

// What the user actually chose in the approval panel — omitted fields mean
// "keep what the system proposed".
export interface ApprovalDecision {
  selected_restaurant?: Record<string, unknown>;
  selected_start_time?: string;
  selected_end_time?: string;
}

export interface ExecutionDetail {
  execution_id: string;
  status: string;
  intent_text: string;
  tasks: TaskSummary[];
  pending_approval: ApprovalProposal | null;
  error: ExecutionError | null;
}

export interface EventSummary {
  event_type: string;
  task_id: string | null;
  agent_id: string | null;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export const TERMINAL_STATUSES = new Set(["COMPLETED", "FAILED", "REJECTED", "CANCELLED"]);
