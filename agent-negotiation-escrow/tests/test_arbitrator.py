import pytest
from arbitrator.stage_a_checks import StageAChecker
from arbitrator.stage_b_llm import TwoStageArbitrator
from engine.transcript import TranscriptEngine
from agents.message_schema import NegotiationMessage, Terms

def test_stage_a_catches_transcript_tampering():
    checker = StageAChecker()
    engine = TranscriptEngine()
    engine.add_message(NegotiationMessage("offer", "buyer", 1, Terms(100.0, "S", "7d"), "R1"))
    engine.add_message(NegotiationMessage("accept", "seller", 1, Terms(100.0, "S", "7d"), "R2"))

    real_hash = engine.compute_commitment_hash()
    fake_hash = "0x" + "f"*64

    res = checker.verify(
        transcript_messages=engine.get_full_transcript(),
        on_chain_transcript_hash=fake_hash,
        on_chain_evidence_hash="0x" + "1"*64,
        on_chain_terms={"price": 100.0},
        dispute_timestamp=1050,
        delivery_signaled_timestamp=1000
    )

    assert res.passed == False
    assert res.flag == "transcript_tampering_suspected"

def test_stage_a_catches_missing_evidence():
    checker = StageAChecker()
    engine = TranscriptEngine()
    engine.add_message(NegotiationMessage("accept", "buyer", 1, Terms(100.0, "S", "7d"), "R"))

    real_hash = engine.compute_commitment_hash()

    res = checker.verify(
        transcript_messages=engine.get_full_transcript(),
        on_chain_transcript_hash=real_hash,
        on_chain_evidence_hash="0x" + "0"*64,
        on_chain_terms={"price": 100.0},
        dispute_timestamp=1050,
        delivery_signaled_timestamp=1000
    )

    assert res.passed == True
    assert res.auto_ruling == "refund_to_buyer"
    assert res.flag == "no_delivery_evidence"

def test_two_stage_arbitrator_end_to_end():
    arbitrator = TwoStageArbitrator()
    engine = TranscriptEngine()
    engine.add_message(NegotiationMessage("accept", "buyer", 1, Terms(100.0, "S", "7d"), "Agreed"))

    real_hash = engine.compute_commitment_hash()

    # Test genuine delivery dispute -> release to seller
    ruling = arbitrator.rule(
        transcript_messages=engine.get_full_transcript(),
        on_chain_transcript_hash=real_hash,
        on_chain_evidence_hash="0x" + "1"*64,
        on_chain_terms={"price": 100.0},
        seller_evidence_content="genuine_delivery proof valid API endpoint 200 OK",
        buyer_dispute_claim="Buyer claims delay"
    )

    assert ruling.decision == "release_to_seller"
    assert ruling.seller_pct == 100
    assert ruling.requires_human_review == False
