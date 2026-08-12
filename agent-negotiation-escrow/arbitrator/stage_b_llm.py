import os
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from arbitrator.stage_a_checks import StageAChecker, StageAResult
from llm.ollama_client import LLMClient

@dataclass
class ArbitrationRuling:
    stage: str  # "A" or "B" or "HUMAN"
    decision: str  # "release_to_seller", "refund_to_buyer", "split", "flagged"
    seller_pct: int
    buyer_pct: int
    confidence: float
    reasoning: str
    requires_human_review: bool

class TwoStageArbitrator:
    def __init__(self, model: str = "qwen2.5-coder:32b", prompts_dir: str = "prompts"):
        self.model = model
        self.prompts_dir = prompts_dir
        self.stage_a = StageAChecker()
        self.llm_client = LLMClient(default_model=model)
        self._load_system_prompt()

    def _load_system_prompt(self):
        path = os.path.join(self.prompts_dir, "arbitrator_system.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.system_prompt_template = f.read()
        else:
            self.system_prompt_template = (
                "You are a neutral arbitrator. Rule on dispute in JSON format:\n"
                "{'decision': 'release_to_seller|refund_to_buyer|split', 'split_pct': {'seller': int, 'buyer': int}, 'confidence': float, 'reasoning': str}"
            )

    def rule(
        self,
        transcript_messages: List[Dict[str, Any]],
        on_chain_transcript_hash: str,
        on_chain_evidence_hash: Optional[str],
        on_chain_terms: Dict[str, Any],
        seller_evidence_content: str,
        buyer_dispute_claim: str,
        dispute_timestamp: int = 1050,
        delivery_signaled_timestamp: int = 1000,
        dispute_window: int = 3600
    ) -> ArbitrationRuling:

        # Step 1: Execute Stage A Deterministic Checks
        stage_a_res: StageAResult = self.stage_a.verify(
            transcript_messages=transcript_messages,
            on_chain_transcript_hash=on_chain_transcript_hash,
            on_chain_evidence_hash=on_chain_evidence_hash,
            on_chain_terms=on_chain_terms,
            dispute_timestamp=dispute_timestamp,
            delivery_signaled_timestamp=delivery_signaled_timestamp,
            dispute_window=dispute_window
        )

        # Tampering detected -> escalate to human review immediately
        if not stage_a_res.passed:
            return ArbitrationRuling(
                stage="A",
                decision="flagged",
                seller_pct=0,
                buyer_pct=0,
                confidence=1.0,
                reasoning=f"Stage A integrity failure: {stage_a_res.reasoning}",
                requires_human_review=True
            )

        # Stage A deterministic auto-ruling (no LLM call needed)
        if stage_a_res.auto_ruling:
            seller_pct = stage_a_res.seller_pct
            buyer_pct = 100 - seller_pct
            return ArbitrationRuling(
                stage="A",
                decision=stage_a_res.auto_ruling,
                seller_pct=seller_pct,
                buyer_pct=buyer_pct,
                confidence=1.0,
                reasoning=stage_a_res.reasoning,
                requires_human_review=False
            )

        # Step 2: Stage B LLM Evaluation
        prompt = self.system_prompt_template.format(
            terms=json.dumps(on_chain_terms, indent=2),
            transcript=json.dumps(transcript_messages, indent=2),
            delivery_evidence=seller_evidence_content,
            dispute_claim=buyer_dispute_claim
        )

        llm_res = self.llm_client.generate_json(prompt, [], model=self.model)

        decision = llm_res.get("decision", "release_to_seller")
        split_dict = llm_res.get("split_pct", {})
        seller_pct = int(split_dict.get("seller", 100 if decision == "release_to_seller" else 0))
        buyer_pct = int(split_dict.get("buyer", 100 - seller_pct))
        confidence = float(llm_res.get("confidence", 0.85))
        reasoning = str(llm_res.get("reasoning", "LLM Stage B arbitration ruling based on evidence review."))

        # Confidence threshold check (NFR/Design requirement: < 0.7 -> human review fallback)
        requires_human = confidence < 0.70

        return ArbitrationRuling(
            stage="B",
            decision="flagged" if requires_human else decision,
            seller_pct=seller_pct,
            buyer_pct=buyer_pct,
            confidence=confidence,
            reasoning=reasoning,
            requires_human_review=requires_human
        )
