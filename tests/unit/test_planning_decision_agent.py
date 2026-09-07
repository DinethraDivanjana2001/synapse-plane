"""Unit tests for PlanningDecisionAgent — pure, no DB, no LLM."""

from demo.seed import build_agent_catalogue

from synapse_plane.agents.base import AgentInput
from synapse_plane.agents.internal.planning_decision import PlanningDecisionAgent, score_candidate
from synapse_plane.domain.tools import RestaurantCandidate
from synapse_plane.planning.fake_planner import DINNER_WORKFLOW_PLAN, FakePlanner

CATALOGUE = build_agent_catalogue()


def make_candidate(**overrides: object) -> RestaurantCandidate:
    defaults: dict[str, object] = {
        "name": "Test Place",
        "cuisine": "italian",
        "rating": 4.0,
        "price_level": "moderate",
        "is_quiet": False,
        "distance_km": 1.0,
        "source": "places_primary_tool",
    }
    defaults.update(overrides)
    return RestaurantCandidate(**defaults)  # type: ignore[arg-type]


def test_score_candidate_rewards_rating_quiet_and_cuisine_match() -> None:
    plain = make_candidate(rating=3.0, is_quiet=False, cuisine="japanese")
    great = make_candidate(rating=5.0, is_quiet=True, cuisine="italian")

    assert score_candidate(great, ["italian"]) > score_candidate(plain, ["italian"])


def test_recommend_picks_highest_scoring_candidate() -> None:
    agent = PlanningDecisionAgent(planner=FakePlanner())
    low = make_candidate(name="Low", rating=3.0, is_quiet=False)
    high = make_candidate(name="High", rating=4.8, is_quiet=True, cuisine="italian")

    top = agent.recommend([low, high], preferred_cuisines=["italian"])

    assert top.name == "High"


async def test_plan_delegates_to_underlying_planner() -> None:
    agent = PlanningDecisionAgent(planner=FakePlanner())

    plan = await agent.plan("Arrange dinner with Maya tomorrow", None, CATALOGUE)  # type: ignore[arg-type]

    assert plan.workflow_id == DINNER_WORKFLOW_PLAN.workflow_id


async def test_execute_returns_top_recommendation() -> None:
    agent = PlanningDecisionAgent(planner=FakePlanner())
    candidates = [
        make_candidate(name="Loud Place", rating=4.0, is_quiet=False).model_dump(mode="json"),
        make_candidate(name="Quiet Place", rating=4.2, is_quiet=True).model_dump(mode="json"),
    ]

    output = await agent.execute(
        AgentInput(
            goal="recommend",
            task_id="t1",
            execution_id="e1",
            context={"candidates": candidates, "preferred_cuisines": ["italian"]},
        )
    )

    assert output.success is True
    assert output.result["selected"]["name"] == "Quiet Place"


def test_health_check_is_true() -> None:
    assert PlanningDecisionAgent(planner=FakePlanner()).health_check() is True
