from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class MotivationalStrategy(str, Enum):
    """The four motivational appeal strategies the agent can use."""
    LOGICAL = "logical"
    EMOTIONAL = "emotional"
    SOCIAL_PROOF = "social_proof"
    GAMIFICATION = "gamification"


@dataclass
class StrategyOutcome:
    """Records the result of using a strategy with a user."""
    user_id: str
    strategy: MotivationalStrategy
    stage_before: str
    response_length: int
    sentiment_score: float
    reward: float
    stage_after: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)