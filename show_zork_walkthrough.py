#!/usr/bin/env python3
"""Display the complete walkthrough for Zork1."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from games.zork_env import TextAdventureEnv

wrapper = TextAdventureEnv(game=sys.argv[1] if len(sys.argv) > 1 else "zork1")
env = wrapper.env

walkthrough = env.get_walkthrough()

print(f"Zork1 Complete Walkthrough ({len(walkthrough)} steps):")
print("=" * 80)

# Show all steps
for i, step in enumerate(walkthrough, 1):
    print(f"{i:3d}. {step}")

env.close()
