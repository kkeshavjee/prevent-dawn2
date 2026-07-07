import logging
from .strategy import MotivationalStrategy, StrategyOutcome

logger = logging.getLogger(__name__)

STAGE_ORDER = [
    "precontemplation",
    "contemplation",
    "preparation",
    "action",
    "maintenance",
]


def compute_reward(response_length: int, sentiment_score: float, stage_before: str, stage_after: str) -> float:
    length_score = min(response_length / 200.0, 1.0)

    stage_score = 0.0
    if stage_before in STAGE_ORDER and stage_after in STAGE_ORDER:
        before_idx = STAGE_ORDER.index(stage_before)
        after_idx = STAGE_ORDER.index(stage_after)
        diff = after_idx - before_idx
        if diff > 0:
            stage_score = 1.0
        elif diff == 0:
            stage_score = 0.3
        else:
            stage_score = -0.5

    reward = (0.3 * length_score) + (0.3 * sentiment_score) + (0.4 * stage_score)
    return round(max(0.0, min(1.0, reward)), 3)


def record_outcome(
    user_id: str,
    strategy: MotivationalStrategy,
    stage_before: str,
    user_response: str,
    sentiment_score: float,
    stage_after: str,
) -> StrategyOutcome:
    response_length = len(user_response)
    reward = compute_reward(response_length, sentiment_score, stage_before, stage_after)

    outcome = StrategyOutcome(
        user_id=user_id,
        strategy=strategy,
        stage_before=stage_before,
        response_length=response_length,
        sentiment_score=sentiment_score,
        reward=reward,
        stage_after=stage_after,
    )

    logger.info(
        f"Strategy outcome recorded | user={user_id} | strategy={strategy.value} "
        f"| reward={reward} | stage={stage_before}->{stage_after}"
    )

    return outcome