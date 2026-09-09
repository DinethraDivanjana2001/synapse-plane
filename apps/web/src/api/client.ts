import type {
  AgentManifest,
  ApprovalDecision,
  EventSummary,
  ExecutionDetail,
  UserProfile,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const V1 = `${API_BASE}/api/v1`;

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function createExecution(
  intent: string,
  injectFailure: boolean,
  preferredTime?: string
): Promise<ExecutionDetail> {
  const res = await fetch(`${V1}/executions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      intent,
      inject_failure: injectFailure,
      preferred_time: preferredTime || null,
    }),
  });
  return json(res);
}

export async function getExecution(id: string): Promise<ExecutionDetail> {
  return json(await fetch(`${V1}/executions/${id}`));
}

export async function getEvents(executionId: string): Promise<EventSummary[]> {
  return json(await fetch(`${V1}/executions/${executionId}/events`));
}

export async function approveAction(
  executionId: string,
  approvalId: string,
  decision: ApprovalDecision = {}
): Promise<ExecutionDetail> {
  return json(
    await fetch(`${V1}/executions/${executionId}/approvals/${approvalId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(decision),
    })
  );
}

export async function rejectAction(
  executionId: string,
  approvalId: string
): Promise<ExecutionDetail> {
  return json(
    await fetch(`${V1}/executions/${executionId}/approvals/${approvalId}/reject`, {
      method: "POST",
    })
  );
}

export async function listAgents(): Promise<AgentManifest[]> {
  return json(await fetch(`${V1}/agents`));
}

export async function getProfile(userId: string): Promise<UserProfile> {
  return json(await fetch(`${V1}/profile/${userId}`));
}
