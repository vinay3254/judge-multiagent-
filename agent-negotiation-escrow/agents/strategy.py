from dataclasses import dataclass
from typing import Literal

StrategyType = Literal["cooperative", "aggressive", "budget_capped", "adversarial"]

@dataclass
class Strategy:
    name: StrategyType
    description: str

    def get_prompt_instructions(self, role: str) -> str:
        if self.name == "cooperative":
            return (
                "Your strategy is COOPERATIVE. You prioritize reaching an equitable deal quickly. "
                "Be willing to make reasonable price concessions if counter-offers are fair."
            )
        elif self.name == "aggressive":
            return (
                "Your strategy is AGGRESSIVE. You anchor hard on your target price and make small, slow concessions. "
                "Push hard to maximize your financial surplus before yielding."
            )
        elif self.name == "budget_capped":
            return (
                "Your strategy is STRICT BUDGET CAPPED / MINIMUM THRESHOLD. "
                "You have a non-negotiable walk-away limit. If the counterpart does not meet your limit by round 5, "
                "send a 'reject' message and walk away cleanly."
            )
        elif self.name == "adversarial":
            return (
                "Your strategy is ADVERSARIAL (Testing Mode). "
                "You will attempt to claim delivery without valid proof or submit fabricated delivery evidence."
            )
        return ""
