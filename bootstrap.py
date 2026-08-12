import os
import yaml

PROJECT_NAME = "agent-negotiation-escrow"
dirs = [
    f"{PROJECT_NAME}/agents",
    f"{PROJECT_NAME}/arbitrator",
    f"{PROJECT_NAME}/engine",
    f"{PROJECT_NAME}/contracts/scripts",
    f"{PROJECT_NAME}/contracts/test",
    f"{PROJECT_NAME}/chain",
    f"{PROJECT_NAME}/llm",
    f"{PROJECT_NAME}/benchmark/scenarios",
    f"{PROJECT_NAME}/prompts",
    f"{PROJECT_NAME}/tests",
]

for d in dirs:
    os.makedirs(d, exist_ok=True)

files = [
    f"{PROJECT_NAME}/agents/__init__.py",
    f"{PROJECT_NAME}/agents/negotiator.py",
    f"{PROJECT_NAME}/agents/strategy.py",
    f"{PROJECT_NAME}/agents/message_schema.py",
    f"{PROJECT_NAME}/arbitrator/__init__.py",
    f"{PROJECT_NAME}/arbitrator/stage_a_checks.py",
    f"{PROJECT_NAME}/arbitrator/stage_b_llm.py",
    f"{PROJECT_NAME}/engine/__init__.py",
    f"{PROJECT_NAME}/engine/negotiation_loop.py",
    f"{PROJECT_NAME}/engine/transcript.py",
    f"{PROJECT_NAME}/contracts/Escrow.sol",
    f"{PROJECT_NAME}/contracts/hardhat.config.js",
    f"{PROJECT_NAME}/contracts/scripts/deploy.js",
    f"{PROJECT_NAME}/contracts/test/Escrow.test.js",
    f"{PROJECT_NAME}/chain/__init__.py",
    f"{PROJECT_NAME}/chain/web3_client.py",
    f"{PROJECT_NAME}/chain/contract_abi.json",
    f"{PROJECT_NAME}/llm/__init__.py",
    f"{PROJECT_NAME}/llm/ollama_client.py",
    f"{PROJECT_NAME}/benchmark/__init__.py",
    f"{PROJECT_NAME}/benchmark/report.py",
    f"{PROJECT_NAME}/benchmark/history.jsonl",
    f"{PROJECT_NAME}/prompts/buyer_system.md",
    f"{PROJECT_NAME}/prompts/seller_system.md",
    f"{PROJECT_NAME}/prompts/arbitrator_system.md",
    f"{PROJECT_NAME}/prompts/CHANGELOG.md",
    f"{PROJECT_NAME}/main.py",
    f"{PROJECT_NAME}/README.md",
]

for f in files:
    if not os.path.exists(f):
        with open(f, "w", encoding="utf-8") as fp:
            fp.write("")

config = {
    "models": {
        "buyer_agent": "qwen2.5-coder:14b",
        "seller_agent": "qwen2.5-coder:14b",
        "arbitrator": "qwen2.5-coder:32b"
    },
    "negotiation": {
        "max_rounds": 10,
        "round_timeout_seconds": 30
    },
    "chain": {
        "network": "hardhat",
        "escrow_contract_address": None,
        "arbitrator_address": None,
        "dispute_window_seconds": 3600,
        "delivery_confirm_timeout_seconds": 3600
    }
}

with open(f"{PROJECT_NAME}/config.yaml", "w", encoding="utf-8") as fp:
    yaml.dump(config, fp, default_flow_style=False)

print(f"Scaffolded {PROJECT_NAME}/ successfully.")
