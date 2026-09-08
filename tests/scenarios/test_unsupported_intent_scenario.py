"""Scenario: an intent requiring a prohibited capability is rejected before
any task runs or any tool is called."""


async def test_unsupported_flight_intent(scenario_client) -> None:
    response = await scenario_client.post(
        "/api/v1/executions",
        json={"intent": "Buy me the cheapest flight to Singapore", "inject_failure": False},
    )

    assert response.status_code == 201
    detail = response.json()
    assert detail["status"] == "FAILED"
    assert detail["error"]["error_code"] == "UNSUPPORTED_CAPABILITY"
    assert "flight.book" in detail["error"]["capabilities"]
    assert detail["tasks"] == []  # no plan was ever validated/stored — nothing ran

    execution_id = detail["execution_id"]
    events = (await scenario_client.get(f"/api/v1/executions/{execution_id}/events")).json()
    event_types = {e["event_type"] for e in events}
    assert "plan.rejected" in event_types
    assert "task.started" not in event_types
    assert "tool.invoked" not in event_types
