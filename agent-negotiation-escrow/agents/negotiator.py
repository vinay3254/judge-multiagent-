import os
import json
from typing import Optional, Dict, Any
from agents.message_schema import NegotiationMessage, Terms, SenderRole
from agents.strategy import Strategy
from llm.ollama_client import LLMClient

class NegotiatorAgent:
    def __init__(
        self,
        role: SenderRole,
        strategy: Strategy,
        budget_cap: float = 100.0,
        minimum_price: float = 60.0,
        wallet_address: str = "0x0000000000000000000000000000000000000000",
        model: str = "qwen2.5-coder:14b",
        prompts_dir: str = "prompts"
    ):
        self.role = role
        self.strategy = strategy
        self.budget_cap = budget_cap
        self.minimum_price = minimum_price
        self.wallet_address = wallet_address
        self.model = model
        self.prompts_dir = prompts_dir

        self.llm_client = LLMClient(default_model=model)
        # Isolated context memory - NEVER shared across agent instances (FR1)
        self._llm_context = []
        self._load_system_prompt()

    def _load_system_prompt(self):
        prompt_filename = f"{self.role}_system.md"
        prompt_path = os.path.join(self.prompts_dir, prompt_filename)

        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()
        else:
            template = (
                f"You are a {self.role.upper()} agent.\n"
                "Strategy: {strategy_instructions}\n"
                "Respond in JSON with schema: {{'type': '...', 'terms': {{'price': float, 'deliverable': str, 'deadline': str}}, 'rationale': str}}"
            )

        strategy_instr = self.strategy.get_prompt_instructions(self.role)
        if self.role == "buyer":
            self.system_prompt = template.format(
                strategy_instructions=strategy_instr,
                budget_cap=self.budget_cap,
                deliverable_requirements="Software / Service Delivery"
            )
        else:
            self.system_prompt = template.format(
                strategy_instructions=strategy_instr,
                minimum_price=self.minimum_price,
                delivery_capability="Verified Service Provider"
            )

    def respond(self, incoming: Optional[NegotiationMessage], current_round: int) -> NegotiationMessage:
        if incoming:
            incoming_dict = incoming.to_dict()
            self._llm_context.append({
                "role": "user",
                "content": json.dumps(incoming_dict)
            })

        # Ask LLM for next action
        raw_res = self.llm_client.generate_json(self.system_prompt, self._llm_context, model=self.model)

        # Schema fallback recovery if malformed
        msg_type = raw_res.get("type", "offer" if current_round == 1 else "counter_offer")
        if msg_type not in ["offer", "counter_offer", "accept", "reject"]:
            msg_type = "counter_offer"

        terms_dict = raw_res.get("terms", {})
        if not isinstance(terms_dict, dict):
            terms_dict = {}

        price = float(terms_dict.get("price", self.budget_cap * 0.8 if self.role == "buyer" else self.minimum_price * 1.2))

        # Hard guardrail check for budget_capped strategy
        if self.strategy.name == "budget_capped":
            if self.role == "buyer" and price > self.budget_cap:
                msg_type = "reject"
            elif self.role == "seller" and price < self.minimum_price:
                msg_type = "reject"

        msg = NegotiationMessage(
            type=msg_type,
            sender=self.role,
            round=current_round,
            terms=Terms(
                price=price,
                deliverable=str(terms_dict.get("deliverable", "Service Delivery")),
                deadline=str(terms_dict.get("deadline", "7 days"))
            ),
            rationale=str(raw_res.get("rationale", "Negotiating optimal terms.")),
        )

        # Append assistant response to private LLM context
        self._llm_context.append({
            "role": "assistant",
            "content": msg.to_json()
        })

        return msg
