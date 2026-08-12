#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="agent-negotiation-escrow"

mkdir -p "$PROJECT_NAME"/{agents,arbitrator,engine,contracts/scripts,chain,llm,benchmark/scenarios,prompts}

touch "$PROJECT_NAME"/agents/__init__.py
touch "$PROJECT_NAME"/agents/negotiator.py
touch "$PROJECT_NAME"/agents/strategy.py
touch "$PROJECT_NAME"/agents/message_schema.py

touch "$PROJECT_NAME"/arbitrator/__init__.py
touch "$PROJECT_NAME"/arbitrator/stage_a_checks.py
touch "$PROJECT_NAME"/arbitrator/stage_b_llm.py

touch "$PROJECT_NAME"/engine/__init__.py
touch "$PROJECT_NAME"/engine/negotiation_loop.py
touch "$PROJECT_NAME"/engine/transcript.py

touch "$PROJECT_NAME"/contracts/Escrow.sol
touch "$PROJECT_NAME"/contracts/hardhat.config.js
touch "$PROJECT_NAME"/contracts/scripts/deploy.js

touch "$PROJECT_NAME"/chain/__init__.py
touch "$PROJECT_NAME"/chain/web3_client.py
touch "$PROJECT_NAME"/chain/contract_abi.json

touch "$PROJECT_NAME"/llm/__init__.py
touch "$PROJECT_NAME"/llm/ollama_client.py

touch "$PROJECT_NAME"/benchmark/__init__.py
touch "$PROJECT_NAME"/benchmark/report.py
touch "$PROJECT_NAME"/benchmark/history.jsonl

touch "$PROJECT_NAME"/prompts/buyer_system.md
touch "$PROJECT_NAME"/prompts/seller_system.md
touch "$PROJECT_NAME"/prompts/arbitrator_system.md
touch "$PROJECT_NAME"/prompts/CHANGELOG.md

cat > "$PROJECT_NAME"/config.yaml << 'EOF'
models:
  buyer_agent: qwen2.5-coder:14b
  seller_agent: qwen2.5-coder:14b
  arbitrator: qwen2.5-coder:32b
negotiation:
  max_rounds: 10
  round_timeout_seconds: 30
chain:
  network: polygon-amoy
  escrow_contract_address: null
  arbitrator_address: null
  dispute_window_seconds: 3600
  delivery_confirm_timeout_seconds: 3600
EOF

touch "$PROJECT_NAME"/main.py
touch "$PROJECT_NAME"/README.md

mkdir -p "$PROJECT_NAME"/specs
cp ./*.md "$PROJECT_NAME"/specs/ 2>/dev/null || true

echo "Scaffolded $PROJECT_NAME/"
echo "Next: implement M1 per 00-workflow-starter.md — contracts/Escrow.sol + Hardhat deploy to Amoy testnet"
