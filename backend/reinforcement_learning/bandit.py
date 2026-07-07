import random
import logging
from dataclasses import dataclass
from typing import Dict

from .strategy import MotivationalStrategy

logger = logging.getLogger(__name__)

EPSILON = 0.15


@dataclass
class StrategyStats:
    """Tracks performance of one strategy for one user."""
    count: int = 0
    total_reward: float = 0.0

    @property
    def average_reward(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total_reward / self.count
    
    

class UserBandit:
    """Epsilon-greedy bandit for a single user."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.stats: Dict[MotivationalStrategy, StrategyStats] = {
            strategy: StrategyStats()
            for strategy in MotivationalStrategy
        }

    def select_strategy(self) -> MotivationalStrategy:
        if random.random() < EPSILON:
            chosen = random.choice(list(MotivationalStrategy))
            logger.info(f"Bandit | user={self.user_id} | exploring -> {chosen.value}")
            return chosen

        untried = [s for s, stats in self.stats.items() if stats.count == 0]
        if untried:
            chosen = random.choice(untried)
            logger.info(f"Bandit | user={self.user_id} | trying untried -> {chosen.value}")
            return chosen

        chosen = max(self.stats, key=lambda s: self.stats[s].average_reward)
        logger.info(
            f"Bandit | user={self.user_id} | exploiting -> {chosen.value} "
            f"(avg_reward={self.stats[chosen].average_reward:.3f})"
        )
        return chosen

    def update(self, strategy: MotivationalStrategy, reward: float) -> None:
        self.stats[strategy].count += 1
        self.stats[strategy].total_reward += reward
        logger.info(
            f"Bandit updated | user={self.user_id} | strategy={strategy.value} "
            f"| reward={reward} | avg={self.stats[strategy].average_reward:.3f} "
            f"| count={self.stats[strategy].count}"
        )

        

class BanditManager:
    """Manages bandit instances for all users."""

    def __init__(self):
        self._bandits: Dict[str, UserBandit] = {}

    def get_or_create(self, user_id: str) -> UserBandit:
        if user_id not in self._bandits:
            self._bandits[user_id] = UserBandit(user_id)
            logger.info(f"Created new bandit for user={user_id}")
        return self._bandits[user_id]

    def select_strategy(self, user_id: str) -> MotivationalStrategy:
        return self.get_or_create(user_id).select_strategy()

    def record_result(self, user_id: str, strategy: MotivationalStrategy, reward: float) -> None:
        self.get_or_create(user_id).update(strategy, reward)

    def get_stats(self, user_id: str) -> Dict[str, dict]:
        bandit = self.get_or_create(user_id)
        return {
            s.value: {
                "count": bandit.stats[s].count,
                "average_reward": bandit.stats[s].average_reward,
            }
            for s in MotivationalStrategy
        }


bandit_manager = BanditManager()