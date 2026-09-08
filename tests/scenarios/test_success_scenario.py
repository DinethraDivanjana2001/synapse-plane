"""Scenario: dinner intent -> parallel discovery/calendar -> approval ->
COMPLETED. Full HTTP stack, real DB, FakePlanner + demo (mock) agents."""


async def test_full_success_workflow(scenario_client) -> None:
    create_response = await scenario_client.post(
        "/api/v1/executions",
        json={"intent": "Arrange dinner with Maya tomorrow", "inject_failure": False},
    )
    assert create_response.status_code == 201
    detail = create_response.json()
    assert detail["status"] == "WAITING_FOR_APPROVAL"
    assert detail["pending_approval"] is not None

    task_statuses = {t["task_id"]: t["status"] for t in detail["tasks"]}
    assert task_statuses["resolve_context"] == "SUCCEEDED"
    assert task_statuses["discover_venues"] == "SUCCEEDED"
    assert task_statuses["check_calendar"] == "SUCCEEDED"
    assert task_statuses["recommend"] == "SUCCEEDED"
    assert task_statuses["create_event"] == "WAITING_FOR_APPROVAL"

    execution_id = detail["execution_id"]
    events = (await scenario_client.get(f"/api/v1/executions/{execution_id}/events")).json()
    event_types = {e["event_type"] for e in events}
    for expected in (
        "execution.created",
        "planning.started",
        "plan.proposed",
        "plan.validated",
        "agent.selected",
        "task.started",
        "task.succeeded",
        "approval.requested",
    ):
        assert expected in event_types, f"missing event: {expected}"

    approval_id = detail["pending_approval"]["proposal_id"]
    approve_response = await scenario_client.post(
        f"/api/v1/executions/{execution_id}/approvals/{approval_id}/approve"
    )
    assert approve_response.status_code == 200
    final = approve_response.json()
    assert final["status"] == "COMPLETED"

    create_event_task = next(t for t in final["tasks"] if t["task_id"] == "create_event")
    assert create_event_task["status"] == "SUCCEEDED"
    assert create_event_task["output"]["event_id"]

    final_events = (await scenario_client.get(f"/api/v1/executions/{execution_id}/events")).json()
    final_event_types = {e["event_type"] for e in final_events}
    assert "approval.approved" in final_event_types
    assert "execution.resumed" in final_event_types
    assert "execution.completed" in final_event_types
