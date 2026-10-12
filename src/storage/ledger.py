import json
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.config.settings import settings

GENESIS_HASH = "0" * 64


class AuditLedger:
    """
    Append-only cryptographically hashed audit ledger.
    Guarantees immutable historical traceability of registered operators,
    logged abuses of authority, and associated investigations.
    """
    def __init__(self, ledger_path: Optional[Path] = None):
        self.ledger_path = ledger_path or settings.LEDGER_PATH
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            self.ledger_path.touch()

    def _get_last_entry(self) -> Optional[Dict[str, Any]]:
        if not self.ledger_path.exists() or self.ledger_path.stat().st_size == 0:
            return None
        last_line = ""
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()
        if last_line:
            try:
                return json.loads(last_line)
            except Exception:
                return None
        return None

    def append_entry(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Appends a new entry to the immutable ledger chained to the previous hash."""
        last_entry = self._get_last_entry()
        if last_entry:
            last_index = last_entry.get("index", 0)
            prev_hash = last_entry.get("hash", GENESIS_HASH)
            next_index = last_index + 1
        else:
            last_index = -1
            prev_hash = GENESIS_HASH
            next_index = 0

        timestamp = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        
        # Calculate SHA-256
        data_to_hash = f"{next_index}:{timestamp}:{action}:{payload_str}:{prev_hash}"
        entry_hash = hashlib.sha256(data_to_hash.encode("utf-8")).hexdigest()

        entry = {
            "index": next_index,
            "timestamp_utc": timestamp,
            "action": action,
            "payload": payload,
            "prev_hash": prev_hash,
            "hash": entry_hash
        }

        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return entry

    def verify_integrity(self) -> (bool, str):
        """Verifies full cryptographic chain from genesis to head."""
        if not self.ledger_path.exists() or self.ledger_path.stat().st_size == 0:
            return True, "Ledger is empty (valid)."

        expected_prev_hash = GENESIS_HASH
        expected_index = 0

        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception as e:
                    return False, f"JSON parse error on line {line_no}: {e}"

                idx = entry.get("index")
                timestamp = entry.get("timestamp_utc")
                action = entry.get("action")
                payload = entry.get("payload")
                prev_hash = entry.get("prev_hash")
                entry_hash = entry.get("hash")

                if idx != expected_index:
                    return False, f"Index mismatch on line {line_no}: expected {expected_index}, got {idx}"

                if prev_hash != expected_prev_hash:
                    return False, f"Broken chain link on line {line_no}: expected prev_hash {expected_prev_hash}, got {prev_hash}"

                payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
                data_to_hash = f"{idx}:{timestamp}:{action}:{payload_str}:{prev_hash}"
                computed_hash = hashlib.sha256(data_to_hash.encode("utf-8")).hexdigest()

                if computed_hash != entry_hash:
                    return False, f"Hash mismatch on line {line_no}: expected {computed_hash}, got {entry_hash}"

                expected_prev_hash = entry_hash
                expected_index += 1

        return True, f"Integrity verified for {expected_index} blocks."

    def read_all_entries(self) -> List[Dict[str, Any]]:
        entries = []
        if not self.ledger_path.exists():
            return entries
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line.strip()))
        return entries
