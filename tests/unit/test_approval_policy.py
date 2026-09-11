"""Approval digest and expiry checks — the step_06 spec requires the approve
endpoint to verify both before resuming a CONSEQUENTIAL_WRITE task."""

from datetime import UTC, datetime, timedelta

from synapse_plane.domain.profile import (
    ApprovalPolicyConfig,
    CalendarConfig,
    FoodPreferences,
    Location,
    TravelPreferences,
    UserProfile,
)
from synapse_plane.policies.approval_policy import ApprovalPolicy


def make_profile() -> UserProfile:
    return UserProfile(
        user_id="user-dinethra",
        display_name="Dinethra",
        home_location=Location(label="Colombo", latitude=6.9271, longitude=79.8612),
        timezone="Asia/Colombo",
        food_preferences=FoodPreferences(cuisines=["italian"]),
        travel_preferences=TravelPreferences(interests=["hiking"]),
        calendar=CalendarConfig(),
        approval_policy=ApprovalPolicyConfig(),
    )


def make_proposal():
    policy = ApprovalPolicy()
    return policy.build_proposal(
        execution_id="exec-1",
        task_id="task-1",
        recommendation={"selected": {"name": "La Foresta", "address": "Colombo 03"}},
        time_slot={
            "start_time": "2026-09-10T19:00:00+05:30",
            "end_time": "2026-09-10T21:00:00+05:30",
        },
        profile=make_profile(),
    )


def test_verify_digest_accepts_a_freshly_built_proposal():
    proposal = make_proposal()
    assert ApprovalPolicy().verify_digest(proposal) is True


def test_verify_digest_survives_a_round_trip_through_string_datetimes():
    # Simulates reloading from the DB, where start_time/end_time come back
    # as real datetime objects rather than the raw strings build_proposal
    # originally received — this is exactly the case that would silently
    # break a naive re-hash of the input dict.
    proposal = make_proposal()
    reloaded = proposal.model_copy(
        update={
            "start_time": datetime.fromisoformat(proposal.start_time.isoformat()),
            "end_time": datetime.fromisoformat(proposal.end_time.isoformat()),
        }
    )
    assert ApprovalPolicy().verify_digest(reloaded) is True


def test_verify_digest_rejects_a_tampered_field():
    proposal = make_proposal()
    tampered = proposal.model_copy(update={"restaurant_name": "Some Other Restaurant"})
    assert ApprovalPolicy().verify_digest(tampered) is False


def test_is_expired_false_for_a_fresh_proposal():
    proposal = make_proposal()
    assert ApprovalPolicy().is_expired(proposal) is False


def test_is_expired_true_past_the_ttl():
    proposal = make_proposal()
    stale = proposal.model_copy(
        update={"expires_at": datetime.now(UTC) - timedelta(hours=1)}
    )
    assert ApprovalPolicy().is_expired(stale) is True
