import pytest
import json
from agents.negotiator import NegotiatorAgent
from agents.strategy import Strategy
from agents.message_schema import NegotiationMessage, Terms
from engine.transcript import TranscriptEngine

def test_buyer_seller_contexts_never_share_state():
    """Verify FR1: Buyer and Seller agent private memory contexts remain strictly isolated."""
    strat = Strategy("cooperative", "")
    buyer = NegotiatorAgent("buyer", strat, budget_cap=100.0)
    seller = NegotiatorAgent("seller", strat, minimum_price=60.0)

    # Mutate buyer's private LLM context
    buyer._llm_context.append({"role": "user", "content": "SECRET_BUYER_THOUGHT"})

    assert len(buyer._llm_context) == 1
    assert len(seller._llm_context) == 0
    assert "SECRET_BUYER_THOUGHT" not in [m["content"] for m in seller._llm_context]

def test_transcript_hash_stable_across_reserialization():
    """Verify transcript hash stability regardless of dictionary key ordering."""
    engine1 = TranscriptEngine()
    engine2 = TranscriptEngine()

    msg1 = NegotiationMessage(type="offer", sender="buyer", round=1, terms=Terms(100.0, "Service", "7 days"), rationale="Rationale A")
    msg2 = NegotiationMessage(type="counter_offer", sender="seller", round=1, terms=Terms(120.0, "Service", "7 days"), rationale="Rationale B")

    engine1.add_message(msg1)
    engine1.add_message(msg2)

    engine2.add_message(msg1)
    engine2.add_message(msg2)

    hash1 = engine1.compute_commitment_hash()
    hash2 = engine2.compute_commitment_hash()

    assert hash1 == hash2
    assert hash1.startswith("0x")
    assert len(hash1) == 66

def test_malformed_json_parsing_recovery():
    """Verify robust recovery when model response contains malformed JSON."""
    from llm.ollama_client import LLMClient
    client = LLMClient()
    parsed = client._parse_json_from_text("Here is my offer: ```json\n{\"type\": \"offer\", \"terms\": {\"price\": 85.0}}\n```")
    assert parsed.get("type") == "offer"
    assert parsed.get("terms", {}).get("price") == 85.0
