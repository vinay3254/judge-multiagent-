from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from engine.transcript import TranscriptEngine

@dataclass
class StageAResult:
    passed: bool
    auto_ruling: Optional[str] = None  # "release_to_seller", "refund_to_buyer", None
    seller_pct: int = 0
    flag: Optional[str] = None  # "transcript_tampering_suspected", "terms_tampering_suspected", "no_delivery_evidence", "late_dispute"
    reasoning: str = ""

class StageAChecker:
    def verify(
        self,
        transcript_messages: List[Dict[str, Any]],
        on_chain_transcript_hash: str,
        on_chain_evidence_hash: Optional[str],
        on_chain_terms: Dict[str, Any],
        dispute_timestamp: int,
        delivery_signaled_timestamp: int,
        dispute_window: int = 3600
    ) -> StageAResult:

        # 1. Verify Transcript Hash Match
        engine = TranscriptEngine()
        from agents.message_schema import NegotiationMessage
        for msg_dict in transcript_messages:
            engine.add_message(NegotiationMessage.from_dict(msg_dict))

        computed_hash = engine.compute_commitment_hash()
        if computed_hash.lower() != on_chain_transcript_hash.lower():
            return StageAResult(
                passed=False,
                flag="transcript_tampering_suspected",
                reasoning=f"Transcript hash mismatch. Computed: {computed_hash}, On-Chain: {on_chain_transcript_hash}"
            )

        # 2. Verify Terms Match Last Accept Message
        accept_msgs = [m for m in transcript_messages if m.get("type") == "accept"]
        if accept_msgs:
            last_accept = accept_msgs[-1]
            accepted_price = float(last_accept.get("terms", {}).get("price", 0))
            on_chain_price = float(on_chain_terms.get("price", 0))

            if abs(accepted_price - on_chain_price) > 0.01:
                return StageAResult(
                    passed=False,
                    flag="terms_tampering_suspected",
                    reasoning=f"Accepted terms price (${accepted_price}) does not match on-chain escrow locked price (${on_chain_price})"
                )

        # 3. Verify Delivery Evidence Hash Presence
        if not on_chain_evidence_hash or on_chain_evidence_hash in ["0x" + "0"*64, "", None]:
            return StageAResult(
                passed=True,
                auto_ruling="refund_to_buyer",
                seller_pct=0,
                flag="no_delivery_evidence",
                reasoning="Seller failed to submit on-chain delivery evidence hash."
            )

        # 4. Dispute Window Check
        if dispute_timestamp > delivery_signaled_timestamp + dispute_window:
            return StageAResult(
                passed=True,
                auto_ruling="release_to_seller",
                seller_pct=100,
                flag="late_dispute",
                reasoning="Buyer filed dispute after allowed dispute window expired."
            )

        # All Stage A deterministic checks passed cleanly!
        return StageAResult(
            passed=True,
            auto_ruling=None,
            reasoning="Stage A deterministic integrity checks passed cleanly."
        )
