from typing import Tuple, Optional
from agents.negotiator import NegotiatorAgent
from agents.message_schema import NegotiationMessage, Terms
from engine.transcript import TranscriptEngine

class NegotiationLoop:
    def __init__(self, buyer_agent: NegotiatorAgent, seller_agent: NegotiatorAgent, max_rounds: int = 10):
        self.buyer = buyer_agent
        self.seller = seller_agent
        self.max_rounds = max_rounds
        self.transcript_engine = TranscriptEngine()

    def run(self) -> Tuple[bool, Optional[Terms], TranscriptEngine, int]:
        """
        Executes turn-based negotiation between buyer and seller.
        Returns: (success_bool, agreed_terms_or_none, transcript_engine, rounds_count)
        """
        last_message: Optional[NegotiationMessage] = None

        for r in range(1, self.max_rounds + 1):
            # 1. Buyer turn
            buyer_msg = self.buyer.respond(last_message, current_round=r)
            self.transcript_engine.add_message(buyer_msg)
            last_message = buyer_msg

            if buyer_msg.type == "accept":
                return True, buyer_msg.terms, self.transcript_engine, r
            elif buyer_msg.type == "reject":
                return False, None, self.transcript_engine, r

            # 2. Seller turn
            seller_msg = self.seller.respond(last_message, current_round=r)
            self.transcript_engine.add_message(seller_msg)
            last_message = seller_msg

            if seller_msg.type == "accept":
                return True, seller_msg.terms, self.transcript_engine, r
            elif seller_msg.type == "reject":
                return False, None, self.transcript_engine, r

        # Reached max_rounds without mutual accept -> deal failed
        return False, None, self.transcript_engine, self.max_rounds
