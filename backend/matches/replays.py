"""Compress and read replay JSON logs stored in SQLite.

Edit this file when replay storage format changes.
Copy the helper style here when adding another compact JSON storage helper.
"""

from __future__ import annotations

import json
import zlib
from typing import Any


def compress_replay(replay: dict[str, Any]) -> bytes:
    return zlib.compress(json.dumps(replay, separators=(",", ":"), sort_keys=True).encode("utf-8"), level=9)


def decompress_replay(blob: bytes | None) -> dict[str, Any] | None:
    if blob is None:
        return None
    return json.loads(zlib.decompress(blob).decode("utf-8"))
