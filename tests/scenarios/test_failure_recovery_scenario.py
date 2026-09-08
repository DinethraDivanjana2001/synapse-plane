"""Scenario: primary venue data source fails -> fallback -> COMPLETED.

v3's catalogue has exactly one agent for web.discover_places (browser-use) —
there is no second agent to fall back to at the executor/router level (that
kind of redundant "same capability, different agent" fallback was removed
in the v1->v3 correction; see docs/AGENT_CATALOGUE.md). So the recovery
this scenario demonstrates is TOOL-level, inside that one agent:
DemoVenueDiscoveryAgent tries PlacesTool first, catches the injected
failure, and falls back to PlacesFallbackTool — the task still succeeds on
the first attempt from the executor's point of view. Executor/router-level
agent-to-agent fallback (a different agent takes over) is covered
separately in tests/integration/test_orchestration.py.
"""


async def test_primary_data_source_failure_and_fallback(scenario_client) -> None:
    response = await scenario_client.post(
        "/api/v1/executions",
        json={"intent": "Arrange dinner with Maya tomorrow", "inject_failure": True},
    )
    assert response.status_code == 201
    detail = response.json()
    assert detail["status"] == "WAITING_FOR_APPROVAL"

    discover_task = next(t for t in detail["tasks"] if t["task_id"] == "discover_venues")
    assert discover_task["status"] == "SUCCEEDED"
    # PlacesFallbackTool's fixed candidate, not PlacesTool's — proves the
    # fallback path actually ran, not just that *some* candidates came back
    fallback_names = {c["name"] for c in discover_task["output"]["candidates"]}
    assert "The Quiet Table" in fallback_names

    execution_id = detail["execution_id"]
    events = (await scenario_client.get(f"/api/v1/executions/{execution_id}/events")).json()
    event_types = [e["event_type"] for e in events]
    # the failure was absorbed inside the agent — the executor/scheduler
    # never saw this task fail
    assert "task.failed" not in event_types
    assert (
        event_types.count("task.succeeded") >= 4
    )  # resolve_context, discover_venues, check_calendar, recommend

    approval_id = detail["pending_approval"]["proposal_id"]
    approve_response = await scenario_client.post(
        f"/api/v1/executions/{execution_id}/approvals/{approval_id}/approve"
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "COMPLETED"
