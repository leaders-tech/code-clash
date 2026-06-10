"""Example Python Snake bot for Code Clash.

Edit this file when the bot interface example changes.
Copy this file when starting a new Python bot.
"""

from __future__ import annotations

import json
import sys


def main() -> None:
    state = json.loads(sys.stdin.read())
    you = next(snake for snake in state["snakes"] if snake["id"] == state["you"])
    head_x, head_y = you["body"][0]
    moves = {
        "RIGHT": (head_x + 1, head_y),
        "DOWN": (head_x, head_y + 1),
        "LEFT": (head_x - 1, head_y),
        "UP": (head_x, head_y - 1),
    }
    occupied = {tuple(cell) for snake in state["snakes"] for cell in snake["body"]}
    for move, (x, y) in moves.items():
        if 0 <= x < state["width"] and 0 <= y < state["height"] and (x, y) not in occupied:
            print(move)
            return
    print("RIGHT")


if __name__ == "__main__":
    main()
