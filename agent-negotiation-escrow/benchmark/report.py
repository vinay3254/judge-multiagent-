import os
import glob
import yaml
import json
from datetime import datetime
from typing import Dict, Any, List

from agents.negotiator import NegotiatorAgent
from agents.strategy import Strategy
from engine.negotiation_loop import NegotiationLoop
from chain.web3_client import Web3EscrowClient
from arbitrator.stage_b_llm import TwoStageArbitrator

class BenchmarkRunner:
    def __init__(self, scenarios_dir: str = "benchmark/scenarios", history_file: str = "benchmark/history.jsonl"):
        self.scenarios_dir = scenarios_dir
        self.history_file = history_file
        self.arbitrator = TwoStageArbitrator()

    def load_scenarios(self) -> List[Dict[str, Any]]:
        scenario_files = sorted(glob.glob(os.path.join(self.scenarios_dir, "*.yaml")))
        scenarios = []
        for sf in scenario_files:
            with open(sf, "r", encoding="utf-8") as f:
                scenarios.append(yaml.safe_load(f))
        return scenarios

    def run_benchmark(self) -> Dict[str, Any]:
        scenarios = self.load_scenarios()

        total_scenarios = len(scenarios)
        deals_reached = 0
        correct_no_deals = 0
        incorrect_no_deals = 0
        applicable_deals = 0

        fairness_deltas = []
        honest_party_losses = 0
        adversarial_scenarios_count = 0

        arbitration_correct = 0
        disputes_count = 0
        false_release_count = 0
        false_refund_count = 0
        stuck_funds_count = 0

        category_breakdown = {}

        for sc in scenarios:
            cat = sc.get("category", "general")
            if cat not in category_breakdown:
                category_breakdown[cat] = {"total": 0, "deals": 0, "disputes": 0, "correct_arbitrations": 0}
            category_breakdown[cat]["total"] += 1

            buyer_strat = Strategy(name=sc["buyer_strategy"], description="Buyer strategy")
            seller_strat = Strategy(name=sc["seller_strategy"], description="Seller strategy")

            buyer = NegotiatorAgent(
                role="buyer",
                strategy=buyer_strat,
                budget_cap=sc["buyer_budget_cap"],
                minimum_price=sc["seller_minimum_price"]
            )
            seller = NegotiatorAgent(
                role="seller",
                strategy=seller_strat,
                budget_cap=sc["buyer_budget_cap"],
                minimum_price=sc["seller_minimum_price"]
            )

            loop = NegotiationLoop(buyer, seller, max_rounds=10)
            agreed, terms, transcript_engine, rounds = loop.run()

            # Process Negotiation Result
            if sc["category"] == "no_deal_expected":
                if not agreed:
                    correct_no_deals += 1
                else:
                    incorrect_no_deals += 1
            else:
                applicable_deals += 1
                if agreed:
                    deals_reached += 1
                    category_breakdown[cat]["deals"] += 1

                    # Compute Fairness Delta if fair range exists
                    fair_min, fair_max = sc.get("fair_price_range", [0, 0])
                    if fair_min > 0 and fair_max > 0:
                        settled_price = terms.price
                        if settled_price < fair_min:
                            delta = ((fair_min - settled_price) / fair_min) * 100
                        elif settled_price > fair_max:
                            delta = ((settled_price - fair_max) / fair_max) * 100
                        else:
                            delta = 0.0
                        fairness_deltas.append(delta)

            # Process Chain Escrow & Dispute / Arbitration Flow if agreed or dispute expected
            if agreed or sc.get("dispute_expected"):
                client = Web3EscrowClient()
                transcript_hash = transcript_engine.compute_commitment_hash()

                # Simulated transcript tampering scenario
                if sc["category"] == "transcript_tampering":
                    transcript_hash = "0x" + "f"*64 # Tampered hash commitment

                contract_addr = client.deploy_contract(buyer.wallet_address, seller.wallet_address, "0xArbitrator", transcript_hash)
                settled_price = terms.price if terms else sc["buyer_budget_cap"] * 0.8
                client.fund(buyer.wallet_address, settled_price)

                if sc.get("delivery_outcome") in ["genuine", "tampered"]:
                    evidence_hash = "0x" + "1"*64
                    client.signal_delivery(seller.wallet_address, evidence_hash)
                elif sc.get("delivery_outcome") == "fabricated":
                    evidence_hash = "0x" + "0"*64 # Missing / empty evidence hash
                    client.signal_delivery(seller.wallet_address, evidence_hash)
                elif sc["category"] == "timeout_no_response":
                    client.signal_delivery(seller.wallet_address, "0x" + "1"*64)
                    client.check_timeout(current_timestamp=5000)

                # Process Dispute Arbitration
                if sc.get("dispute_expected"):
                    disputes_count += 1
                    category_breakdown[cat]["disputes"] += 1
                    client.dispute_delivery(buyer.wallet_address, "0x" + "9"*64, current_timestamp=1050)

                    ruling = self.arbitrator.rule(
                        transcript_messages=transcript_engine.get_full_transcript(),
                        on_chain_transcript_hash=client.mock_chain_state["transcript_hash"],
                        on_chain_evidence_hash=client.mock_chain_state["evidence_hash"],
                        on_chain_terms={"price": settled_price, "deliverable": "Service", "deadline": "7 days"},
                        seller_evidence_content=sc.get("seller_evidence", "Proof of deliverable"),
                        buyer_dispute_claim=sc.get("buyer_claim", "Dispute claim"),
                    )

                    # Execute Ruling on Smart Contract
                    decision_code = 0 if ruling.decision == "release_to_seller" else (1 if ruling.decision == "refund_to_buyer" else 2)
                    client.arbitrate("0xArbitrator", decision_code, ruling.seller_pct)

                    expected_ruling = sc.get("known_ground_truth_ruling")
                    if ruling.decision == expected_ruling:
                        arbitration_correct += 1
                        category_breakdown[cat]["correct_arbitrations"] += 1
                    else:
                        if expected_ruling == "release_to_seller" and ruling.decision == "refund_to_buyer":
                            false_refund_count += 1
                            honest_party_losses += 1
                        elif expected_ruling == "refund_to_buyer" and ruling.decision == "release_to_seller":
                            false_release_count += 1
                            honest_party_losses += 1
                        elif expected_ruling == "flagged" and ruling.requires_human_review:
                            arbitration_correct += 1
                            category_breakdown[cat]["correct_arbitrations"] += 1

                    if sc.get("delivery_outcome") in ["fabricated", "tampered"]:
                        adversarial_scenarios_count += 1

                # Check stuck funds invariant
                final_state = client.mock_chain_state["state"]
                if final_state in ["Created", "Funded", "DeliverySignaled", "Disputed"]:
                    # Attempt timeout resolution
                    resolved = client.check_timeout(current_timestamp=10000)
                    if resolved in ["Created", "Funded", "DeliverySignaled", "Disputed"]:
                        stuck_funds_count += 1

        deal_success_rate = (deals_reached / applicable_deals * 100) if applicable_deals > 0 else 0.0
        avg_fairness_delta = (sum(fairness_deltas) / len(fairness_deltas)) if fairness_deltas else 0.0
        arbitration_accuracy = (arbitration_correct / disputes_count * 100) if disputes_count > 0 else 100.0
        honest_loss_rate = (honest_party_losses / adversarial_scenarios_count * 100) if adversarial_scenarios_count > 0 else 0.0

        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_scenarios": total_scenarios,
            "deals_reached": deals_reached,
            "applicable_deals": applicable_deals,
            "correct_no_deals": correct_no_deals,
            "incorrect_no_deals": incorrect_no_deals,
            "deal_success_rate_pct": round(deal_success_rate, 2),
            "avg_fairness_delta_pct": round(avg_fairness_delta, 2),
            "adversarial_robustness_honest_loss_pct": round(honest_loss_rate, 2),
            "arbitration_accuracy_pct": round(arbitration_accuracy, 2),
            "false_release_count": false_release_count,
            "false_refund_count": false_refund_count,
            "stuck_funds_count": stuck_funds_count,
            "category_breakdown": category_breakdown
        }

        # Save to history file
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(report) + "\n")

        return report

    def format_report_text(self, report: Dict[str, Any]) -> str:
        lines = [
            f"Run Timestamp: {report['timestamp']}",
            f"Scenarios: {report['total_scenarios']} | Deals reached: {report['deals_reached']} | No-deal (correct): {report['correct_no_deals']} | No-deal (incorrect): {report['incorrect_no_deals']}",
            f"",
            f"Deal success rate: {report['deals_reached']}/{report['applicable_deals']} applicable ({report['deal_success_rate_pct']}%)",
            f"Fairness delta (avg, deals within fair range): {report['avg_fairness_delta_pct']}%",
            f"Adversarial robustness: honest-party fund loss rate: {report['adversarial_robustness_honest_loss_pct']}%",
            f"Arbitration accuracy: {report['arbitration_accuracy_pct']}%",
            f"  False-release rate: {report['false_release_count']} incidents",
            f"  False-refund rate: {report['false_refund_count']} incidents",
            f"Stuck-fund incidents: {report['stuck_funds_count']}",
            f"",
            f"Per-category breakdown:"
        ]
        for cat, data in report["category_breakdown"].items():
            lines.append(f"  - {cat}: {data['deals']}/{data['total']} deals, {data['correct_arbitrations']}/{data['disputes']} arbitrations correct")

        return "\n".join(lines)
