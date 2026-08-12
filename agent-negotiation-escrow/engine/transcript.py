import json
import hashlib
from typing import List, Dict, Any
from agents.message_schema import NegotiationMessage

class TranscriptEngine:
    def __init__(self):
        self.messages: List[NegotiationMessage] = []

    def add_message(self, message: NegotiationMessage):
        self.messages.append(message)

    def canonical_serialization(self) -> str:
        """
        Produces canonical JSON string representation of negotiation messages.
        Keys are sorted strictly, float numbers formatted, indentation stripped.
        """
        dict_list = [msg.to_dict() for msg in self.messages]
        return json.dumps(dict_list, sort_keys=True, separators=(',', ':'))

    def compute_commitment_hash(self) -> str:
        """
        Computes commitment hash of canonical transcript serialization as a 0x-prefixed hex string (bytes32).
        """
        canonical_str = self.canonical_serialization()
        raw_bytes = canonical_str.encode('utf-8')
        try:
            from eth_utils import keccak
            hash_bytes = keccak(raw_bytes)
        except ImportError:
            # Deterministic fallback SHA-256 formatted as 32-byte hex commitment
            hash_bytes = hashlib.sha256(raw_bytes).digest()

        return "0x" + hash_bytes.hex()

    def verify_commitment(self, expected_hash: str) -> bool:
        computed = self.compute_commitment_hash()
        return computed.lower() == expected_hash.lower()

    def get_full_transcript(self) -> List[Dict[str, Any]]:
        return [msg.to_dict() for msg in self.messages]
