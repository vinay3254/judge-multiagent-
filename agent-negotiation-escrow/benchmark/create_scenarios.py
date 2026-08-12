import os
import yaml

scenarios = [
    # 1. Easy Convergence (4)
    {"id": "scenario_001", "category": "easy_convergence", "buyer_strategy": "cooperative", "seller_strategy": "cooperative", "buyer_budget_cap": 100.0, "seller_minimum_price": 60.0, "fair_price_range": [70, 90], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": None},
    {"id": "scenario_002", "category": "easy_convergence", "buyer_strategy": "cooperative", "seller_strategy": "cooperative", "buyer_budget_cap": 150.0, "seller_minimum_price": 90.0, "fair_price_range": [100, 130], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": None},
    {"id": "scenario_003", "category": "easy_convergence", "buyer_strategy": "cooperative", "seller_strategy": "cooperative", "buyer_budget_cap": 80.0, "seller_minimum_price": 50.0, "fair_price_range": [55, 75], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": None},
    {"id": "scenario_004", "category": "easy_convergence", "buyer_strategy": "cooperative", "seller_strategy": "cooperative", "buyer_budget_cap": 200.0, "seller_minimum_price": 120.0, "fair_price_range": [140, 180], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": None},

    # 2. No Deal Expected (3)
    {"id": "scenario_005", "category": "no_deal_expected", "buyer_strategy": "budget_capped", "seller_strategy": "budget_capped", "buyer_budget_cap": 50.0, "seller_minimum_price": 80.0, "fair_price_range": [0, 0], "delivery_outcome": "none", "dispute_expected": False, "known_ground_truth_ruling": None},
    {"id": "scenario_006", "category": "no_deal_expected", "buyer_strategy": "budget_capped", "seller_strategy": "aggressive", "buyer_budget_cap": 70.0, "seller_minimum_price": 100.0, "fair_price_range": [0, 0], "delivery_outcome": "none", "dispute_expected": False, "known_ground_truth_ruling": None},
    {"id": "scenario_007", "category": "no_deal_expected", "buyer_strategy": "cooperative", "seller_strategy": "budget_capped", "buyer_budget_cap": 40.0, "seller_minimum_price": 90.0, "fair_price_range": [0, 0], "delivery_outcome": "none", "dispute_expected": False, "known_ground_truth_ruling": None},

    # 3. Hard Bargaining (3)
    {"id": "scenario_008", "category": "hard_bargaining", "buyer_strategy": "aggressive", "seller_strategy": "aggressive", "buyer_budget_cap": 120.0, "seller_minimum_price": 80.0, "fair_price_range": [90, 110], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": None},
    {"id": "scenario_009", "category": "hard_bargaining", "buyer_strategy": "aggressive", "seller_strategy": "aggressive", "buyer_budget_cap": 250.0, "seller_minimum_price": 150.0, "fair_price_range": [180, 220], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": None},
    {"id": "scenario_010", "category": "hard_bargaining", "buyer_strategy": "aggressive", "seller_strategy": "aggressive", "buyer_budget_cap": 90.0, "seller_minimum_price": 60.0, "fair_price_range": [70, 85], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": None},

    # 4. Asymmetric Strategy (3)
    {"id": "scenario_011", "category": "asymmetric_strategy", "buyer_strategy": "cooperative", "seller_strategy": "aggressive", "buyer_budget_cap": 100.0, "seller_minimum_price": 50.0, "fair_price_range": [65, 85], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": None},
    {"id": "scenario_012", "category": "asymmetric_strategy", "buyer_strategy": "aggressive", "seller_strategy": "cooperative", "buyer_budget_cap": 100.0, "seller_minimum_price": 50.0, "fair_price_range": [65, 85], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": None},
    {"id": "scenario_013", "category": "asymmetric_strategy", "buyer_strategy": "budget_capped", "seller_strategy": "cooperative", "buyer_budget_cap": 110.0, "seller_minimum_price": 70.0, "fair_price_range": [80, 100], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": None},

    # 5. Genuine Delivery Dispute (Bad-Faith Buyer) (2)
    {"id": "scenario_014", "category": "genuine_delivery_dispute", "buyer_strategy": "cooperative", "seller_strategy": "cooperative", "buyer_budget_cap": 100.0, "seller_minimum_price": 60.0, "fair_price_range": [70, 90], "delivery_outcome": "genuine", "dispute_expected": True, "known_ground_truth_ruling": "release_to_seller", "seller_evidence": "Valid cryptographic hash of completed API integration code and test execution output.", "buyer_claim": "Buyer claims code was not delivered even though git commit exists."},
    {"id": "scenario_015", "category": "genuine_delivery_dispute", "buyer_strategy": "aggressive", "seller_strategy": "cooperative", "buyer_budget_cap": 150.0, "seller_minimum_price": 80.0, "fair_price_range": [100, 130], "delivery_outcome": "genuine", "dispute_expected": True, "known_ground_truth_ruling": "release_to_seller", "seller_evidence": "Server deployment logs with 200 OK healthcheck proof.", "buyer_claim": "Buyer claims deployment failed due to personal preference change."},

    # 6. Fabricated Delivery Dispute (Lying Seller) (3)
    {"id": "scenario_016", "category": "fabricated_delivery_dispute", "buyer_strategy": "cooperative", "seller_strategy": "adversarial", "buyer_budget_cap": 100.0, "seller_minimum_price": 60.0, "fair_price_range": [70, 90], "delivery_outcome": "fabricated", "dispute_expected": True, "known_ground_truth_ruling": "refund_to_buyer", "seller_evidence": "Empty evidence string.", "buyer_claim": "Seller signaled delivery without providing any software deliverables."},
    {"id": "scenario_017", "category": "fabricated_delivery_dispute", "buyer_strategy": "cooperative", "seller_strategy": "adversarial", "buyer_budget_cap": 120.0, "seller_minimum_price": 70.0, "fair_price_range": [80, 100], "delivery_outcome": "fabricated", "dispute_expected": True, "known_ground_truth_ruling": "refund_to_buyer", "seller_evidence": "Fabricated placeholder text with missing file checksum.", "buyer_claim": "Seller uploaded dummy empty text file instead of negotiated application code."},
    {"id": "scenario_018", "category": "fabricated_delivery_dispute", "buyer_strategy": "cooperative", "seller_strategy": "adversarial", "buyer_budget_cap": 200.0, "seller_minimum_price": 100.0, "fair_price_range": [130, 170], "delivery_outcome": "fabricated", "dispute_expected": True, "known_ground_truth_ruling": "refund_to_buyer", "seller_evidence": "Corrupted zip archive hash.", "buyer_claim": "File archive provided by seller is corrupted and empty."},

    # 7. Transcript Tampering (1)
    {"id": "scenario_019", "category": "transcript_tampering", "buyer_strategy": "cooperative", "seller_strategy": "cooperative", "buyer_budget_cap": 100.0, "seller_minimum_price": 60.0, "fair_price_range": [70, 90], "delivery_outcome": "tampered", "dispute_expected": True, "known_ground_truth_ruling": "flagged", "seller_evidence": "Some proof", "buyer_claim": "Transcript was altered post-hoc"},

    # 8. Timeout No Response (1)
    {"id": "scenario_020", "category": "timeout_no_response", "buyer_strategy": "cooperative", "seller_strategy": "cooperative", "buyer_budget_cap": 100.0, "seller_minimum_price": 60.0, "fair_price_range": [70, 90], "delivery_outcome": "genuine", "dispute_expected": False, "known_ground_truth_ruling": "release_to_seller"}
]

out_dir = os.path.join(os.path.dirname(__file__), "scenarios")
os.makedirs(out_dir, exist_ok=True)

for sc in scenarios:
    filepath = os.path.join(out_dir, f"{sc['id']}.yaml")
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(sc, f, default_flow_style=False)

print(f"Seeded {len(scenarios)} benchmark scenarios in {out_dir}/")
