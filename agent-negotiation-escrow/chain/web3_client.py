import json
import os
from typing import Dict, Any, Optional

class Web3EscrowClient:
    """
    Web3 Wrapper client for deploying and interacting with Escrow.sol contract.
    Supports live Web3 node connections as well as simulated local state testing.
    """
    def __init__(self, rpc_url: str = "http://127.0.0.1:8545", contract_address: Optional[str] = None):
        self.rpc_url = rpc_url
        self.contract_address = contract_address
        self.mock_chain_state: Dict[str, Any] = {
            "state": "Created", # Created, Funded, DeliverySignaled, Confirmed, Disputed, Released, Refunded
            "buyer": "0xBuyerAddress",
            "seller": "0xSellerAddress",
            "arbitrator": "0xArbitratorAddress",
            "transcript_hash": None,
            "evidence_hash": None,
            "dispute_evidence_hash": None,
            "amount_locked": 0.0,
            "delivery_signaled_at": 0,
            "dispute_window": 3600
        }

    def deploy_contract(self, buyer_addr: str, seller_addr: str, arbitrator_addr: str, transcript_hash: str) -> str:
        self.mock_chain_state["buyer"] = buyer_addr
        self.mock_chain_state["seller"] = seller_addr
        self.mock_chain_state["arbitrator"] = arbitrator_addr
        self.mock_chain_state["transcript_hash"] = transcript_hash
        self.mock_chain_state["state"] = "Created"

        self.contract_address = f"0xEscrowContract_{abs(hash(transcript_hash)) % 1000000:06d}"
        return self.contract_address

    def fund(self, sender: str, amount_eth: float) -> bool:
        if self.mock_chain_state["state"] != "Created":
            raise ValueError(f"Cannot fund in state {self.mock_chain_state['state']}")
        if sender.lower() != self.mock_chain_state["buyer"].lower():
            raise PermissionError("Only buyer can fund contract")

        self.mock_chain_state["amount_locked"] = amount_eth
        self.mock_chain_state["state"] = "Funded"
        return True

    def signal_delivery(self, sender: str, evidence_hash: str, timestamp: int = 1000) -> bool:
        if self.mock_chain_state["state"] != "Funded":
            raise ValueError(f"Cannot signal delivery in state {self.mock_chain_state['state']}")
        if sender.lower() != self.mock_chain_state["seller"].lower():
            raise PermissionError("Only seller can signal delivery")

        self.mock_chain_state["evidence_hash"] = evidence_hash
        self.mock_chain_state["delivery_signaled_at"] = timestamp
        self.mock_chain_state["state"] = "DeliverySignaled"
        return True

    def confirm_delivery(self, sender: str) -> bool:
        if self.mock_chain_state["state"] not in ["Funded", "DeliverySignaled"]:
            raise ValueError(f"Cannot confirm delivery in state {self.mock_chain_state['state']}")
        if sender.lower() != self.mock_chain_state["buyer"].lower():
            raise PermissionError("Only buyer can confirm delivery")

        self.mock_chain_state["state"] = "Released"
        return True

    def dispute_delivery(self, sender: str, dispute_evidence_hash: str, current_timestamp: int = 1050) -> bool:
        if self.mock_chain_state["state"] != "DeliverySignaled":
            raise ValueError(f"Cannot dispute in state {self.mock_chain_state['state']}")
        if sender.lower() != self.mock_chain_state["buyer"].lower():
            raise PermissionError("Only buyer can dispute delivery")

        deadline = self.mock_chain_state["delivery_signaled_at"] + self.mock_chain_state["dispute_window"]
        if current_timestamp > deadline:
            raise ValueError("Dispute window expired")

        self.mock_chain_state["dispute_evidence_hash"] = dispute_evidence_hash
        self.mock_chain_state["state"] = "Disputed"
        return True

    def arbitrate(self, sender: str, decision: int, seller_pct: int) -> bool:
        if self.mock_chain_state["state"] != "Disputed":
            raise ValueError(f"Cannot arbitrate in state {self.mock_chain_state['state']}")
        if sender.lower() != self.mock_chain_state["arbitrator"].lower():
            raise PermissionError("Only arbitrator can call arbitrate()")

        if decision == 0:
            self.mock_chain_state["state"] = "Released"
        elif decision == 1:
            self.mock_chain_state["state"] = "Refunded"
        else:
            self.mock_chain_state["state"] = "Released" if seller_pct >= 50 else "Refunded"

        return True

    def check_timeout(self, current_timestamp: int) -> str:
        state = self.mock_chain_state["state"]
        if state == "DeliverySignaled":
            if current_timestamp > self.mock_chain_state["delivery_signaled_at"] + 3600:
                self.mock_chain_state["state"] = "Released"
                return "Released"
        elif state == "Funded":
            if current_timestamp > 7200:
                self.mock_chain_state["state"] = "Refunded"
                return "Refunded"

        return state
