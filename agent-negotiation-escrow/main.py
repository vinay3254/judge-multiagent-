import sys
import argparse
import json
from agents.negotiator import NegotiatorAgent
from agents.strategy import Strategy
from engine.negotiation_loop import NegotiationLoop
from arbitrator.stage_b_llm import TwoStageArbitrator
from benchmark.report import BenchmarkRunner

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Negotiation & On-Chain Settlement Engine")
    parser.add_argument("--benchmark", action="store_true", help="Run full 20-scenario benchmark suite")
    parser.add_argument("--negotiate", action="store_true", help="Run a single negotiation session")
    parser.add_argument("--buyer-strategy", type=str, default="cooperative", help="Buyer strategy: cooperative|aggressive|budget_capped")
    parser.add_argument("--seller-strategy", type=str, default="cooperative", help="Seller strategy: cooperative|aggressive|budget_capped")
    parser.add_argument("--budget", type=float, default=100.0, help="Buyer budget cap")
    parser.add_argument("--min-price", type=float, default=60.0, help="Seller minimum price threshold")
    args = parser.parse_args()

    if args.benchmark or len(sys.argv) == 1:
        print("Executing Multi-Agent Negotiation Benchmark Suite (20 Scenarios)...")
        runner = BenchmarkRunner()
        report = runner.run_benchmark()
        print("\n" + "="*60)
        print("BENCHMARK REPORT RESULTS")
        print("="*60)
        print(runner.format_report_text(report))
        print("="*60)

    elif args.negotiate:
        print(f"Starting single negotiation: Buyer ({args.buyer_strategy}, cap=${args.budget}) vs Seller ({args.seller_strategy}, min=${args.min_price})...")
        buyer = NegotiatorAgent("buyer", Strategy(args.buyer_strategy, ""), budget_cap=args.budget, minimum_price=args.min_price)
        seller = NegotiatorAgent("seller", Strategy(args.seller_strategy, ""), budget_cap=args.budget, minimum_price=args.min_price)

        loop = NegotiationLoop(buyer, seller, max_rounds=10)
        agreed, terms, transcript_engine, rounds = loop.run()

        print(f"\nNegotiation Completed in {rounds} rounds.")
        print(f"Outcome: {'AGREED' if agreed else 'NO DEAL'}")
        if agreed and terms:
            print(f"Agreed Terms: Price=${terms.price}, Deliverable='{terms.deliverable}', Deadline='{terms.deadline}'")

        commitment_hash = transcript_engine.compute_commitment_hash()
        print(f"On-Chain Transcript Commitment Hash: {commitment_hash}")
        print("\nTranscript Messages:")
        for m in transcript_engine.get_full_transcript():
            print(f"  [Round {m['round']}] {m['sender'].upper()} ({m['type']}): ${m['terms']['price']} - '{m['rationale']}'")

if __name__ == "__main__":
    main()
