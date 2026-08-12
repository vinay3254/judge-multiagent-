from dataclasses import dataclass, asdict
from typing import Literal, Optional, Dict, Any
import json
from datetime import datetime, timezone

MessageType = Literal["offer", "counter_offer", "accept", "reject", "delivery_signal", "dispute"]
SenderRole = Literal["buyer", "seller"]

@dataclass
class Terms:
    price: float
    deliverable: str
    deadline: str  # ISO 8601 string or descriptive date

    def to_dict(self) -> Dict[str, Any]:
        return {
            "price": round(float(self.price), 2),
            "deliverable": str(self.deliverable).strip(),
            "deadline": str(self.deadline).strip()
        }

@dataclass
class NegotiationMessage:
    type: MessageType
    sender: SenderRole
    round: int
    terms: Terms
    rationale: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if isinstance(self.terms, dict):
            self.terms = Terms(**self.terms)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "sender": self.sender,
            "round": int(self.round),
            "terms": self.terms.to_dict(),
            "rationale": str(self.rationale),
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NegotiationMessage":
        terms_data = data.get("terms", {})
        if isinstance(terms_data, dict):
            terms_obj = Terms(
                price=float(terms_data.get("price", 0.0)),
                deliverable=str(terms_data.get("deliverable", "Service")),
                deadline=str(terms_data.get("deadline", "7 days"))
            )
        else:
            terms_obj = Terms(price=0.0, deliverable="Service", deadline="7 days")

        return cls(
            type=data.get("type", "offer"),
            sender=data.get("sender", "buyer"),
            round=int(data.get("round", 1)),
            terms=terms_obj,
            rationale=str(data.get("rationale", "")),
            timestamp=str(data.get("timestamp", ""))
        )
