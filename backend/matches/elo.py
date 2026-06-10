"""Update global Elo ratings for bot versions after matches.

Edit this file when ranking math changes.
Copy this file if another simple rating system is added.
"""

from __future__ import annotations


def update_multiplayer_elo(old_ratings: dict[int, float], points: dict[int, float], k: float = 32.0) -> dict[int, float]:
    changes = {version_id: 0.0 for version_id in old_ratings}
    ids = list(old_ratings)
    for index, left in enumerate(ids):
        for right in ids[index + 1 :]:
            expected_left = 1.0 / (1.0 + 10 ** ((old_ratings[right] - old_ratings[left]) / 400.0))
            if points[left] > points[right]:
                score_left = 1.0
            elif points[left] < points[right]:
                score_left = 0.0
            else:
                score_left = 0.5
            delta = k * (score_left - expected_left)
            changes[left] += delta
            changes[right] -= delta
    return {version_id: round(max(100.0, old_ratings[version_id] + changes[version_id]), 2) for version_id in old_ratings}
