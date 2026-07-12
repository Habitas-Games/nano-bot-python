#!/usr/bin/env python3
"""Entry point: python run_headless.py --map maps/bone_maze.json --strategy_a ... --strategy_b ..."""

import sys

from nanobot.runner.headless_runner import run_from_argv

if __name__ == "__main__":
    sys.exit(run_from_argv(sys.argv[1:]))
