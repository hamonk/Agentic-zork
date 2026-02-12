#!/usr/bin/env python3
"""
Text Adventure Agent Runner

Run the MCP ReAct agent to play text adventure games like Zork.

Usage:
    python run_agent.py
    python run_agent.py --game advent
    python run_agent.py --max-steps 50
    python run_agent.py --agent hidden_submission

Examples:
    # Run on Zork 1 with example agent (default)
    python run_agent.py

    # Play a different game
    python run_agent.py --game advent

    # Use a different agent folder
    python run_agent.py --agent hidden_submission

    # List all available games
    python run_agent.py --list-games

    # Run with verbose output
    python run_agent.py -v
"""

import argparse
import sys
import os
import asyncio
from pathlib import Path

# Add games module to path for discovering available games
sys.path.insert(0, str(Path(__file__).parent))
from games.zork_env import list_available_games


def find_agent_folders() -> list[str]:
    """Find all folders containing agent.py and mcp_server.py."""
    project_root = Path(__file__).parent
    agent_folders = []
    
    for folder in project_root.iterdir():
        if folder.is_dir():
            agent_file = folder / "agent.py"
            server_file = folder / "mcp_server.py"
            if agent_file.exists() and server_file.exists():
                agent_folders.append(folder.name)
    
    return sorted(agent_folders)


async def run_walkthrough_cheat(args):
    """Run the game's official walkthrough (cheat mode)."""
    from games.zork_env import TextAdventureEnv
    
    print(f"\n[CHEAT MODE] Executing official walkthrough for {args.game}")
    print("=" * 60)
    
    wrapper = TextAdventureEnv(game=args.game)
    env = wrapper.env
    
    try:
        walkthrough = env.get_walkthrough()
    except Exception as e:
        print(f"Error: Could not get walkthrough for {args.game}: {e}")
        env.close()
        return None
    
    print(f"Walkthrough has {len(walkthrough)} steps\n")
    
    # Reset environment
    state = wrapper.reset()
    locations_visited = set()
    
    print(f"Starting location: {state.observation.split(chr(10))[0]}\n")
    
    # Execute each step
    for i, action in enumerate(walkthrough[:args.max_steps], 1):
        if args.verbose:
            print(f"\n--- Step {i}/{len(walkthrough)} ---")
            print(f"Action: {action}")
        else:
            print(f"{i:3d}. {action}", end="")
        
        state = wrapper.step(action)
        
        # Track location
        location = state.observation.split('\n')[0] if state.observation else "Unknown"
        locations_visited.add(location)
        
        if args.verbose:
            print(f"\nResult:\n{state.observation}\n")
            print(f"Score: {state.score} | Moves: {state.moves} | Reward: {state.reward}")
        else:
            score_str = f" → Score: {state.score}" if state.reward > 0 else ""
            print(score_str)
        
        if state.done:
            print(f"\n\n[GAME OVER at step {i}]")
            break
    
    env.close()
    
    # Return results in same format as agent
    from dataclasses import dataclass
    @dataclass
    class WalkthroughResult:
        final_score: int
        max_score: int
        moves: int
        locations_visited: set
        game_completed: bool
        error: str = None
        history: list = None
    
    return WalkthroughResult(
        final_score=state.score,
        max_score=350,  # Zork default
        moves=state.moves,
        locations_visited=locations_visited,
        game_completed=state.done,
        history=[]
    )


async def run_mcp_agent(args):
    """Run MCP ReAct Agent from the specified folder."""
    agent_folder = Path(__file__).parent / args.agent
    agent_file = agent_folder / "agent.py"
    server_file = agent_folder / "mcp_server.py"
    
    # Validate folder structure
    if not agent_folder.exists():
        raise FileNotFoundError(f"Agent folder not found: {agent_folder}")
    if not agent_file.exists():
        raise FileNotFoundError(f"agent.py not found in {agent_folder}")
    if not server_file.exists():
        raise FileNotFoundError(f"mcp_server.py not found in {agent_folder}")
    
    # Import from the specified folder
    sys.path.insert(0, str(agent_folder))
    from agent import StudentAgent
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    print(f"\n[MCP] Running Student Agent with FastMCP")
    print(f"   Agent: {args.agent}/")
    print(f"   Game: {args.game}")
    if args.cheat:
        print(f"   Mode: CHEAT (Walkthrough hints enabled)")
    print()

    agent = StudentAgent()
    
    # Get walkthrough if regular cheat mode (not super-cheat)
    walkthrough = None
    if args.cheat and not args.super_cheat:
        from games.zork_env import TextAdventureEnv
        wrapper = TextAdventureEnv(game=args.game)
        try:
            walkthrough = wrapper.env.get_walkthrough()
            print(f"[CHEAT] Loaded {len(walkthrough)} walkthrough steps as hints\n")
        except Exception as e:
            print(f"[WARNING] Could not load walkthrough: {e}\n")
        wrapper.env.close()
    
    # Create transport for the MCP server
    env_vars = os.environ.copy()
    env_vars["GAME"] = args.game
    
    transport = StdioTransport(
        command=sys.executable,
        args=[str(server_file)],
        env=env_vars,
    )

    async with Client(transport) as client:
        return await agent.run(
            client=client,
            game=args.game,
            max_steps=args.max_steps,
            seed=42,  # Using a fixed seed for direct running
            verbose=args.verbose,
            walkthrough=walkthrough,
        )


def main():
    # Find available agent folders
    agent_folders = find_agent_folders()
    
    parser = argparse.ArgumentParser(
        description="Run the MCP ReAct agent to play text adventure games",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python run_agent.py                           # Play Zork 1 with example agent
  python run_agent.py --game advent             # Play Adventure
  python run_agent.py --agent hidden_submission # Use hidden agent
  python run_agent.py --list-games              # List all games
  python run_agent.py --list-agents             # List all agent folders
  python run_agent.py -v                        # Verbose output
        """
    )

    # Get available games for help text
    available_games = list_available_games()
    game_help = f"Game to play (default: zork1). {len(available_games)} games available."
    agent_help = f"Agent folder to use (default: example_submission). Available: {', '.join(agent_folders)}"

    parser.add_argument(
        "--agent", "-a",
        type=str,
        default="example_submission",
        help=agent_help
    )
    parser.add_argument(
        "--game", "-g",
        type=str,
        default="lostpig",
        help=game_help
    )
    parser.add_argument(
        "--list-games",
        action="store_true",
        help="List all available games and exit"
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List all available agent folders and exit"
    )
    parser.add_argument(
        "--max-steps", "-n",
        type=int,
        default=100,
        help="Maximum number of steps to run (default: 100)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed reasoning from the agent"
    )
    parser.add_argument(
        "--cheat",
        action="store_true",
        help="Provide optimal walkthrough as hints to the agent"
    )
    parser.add_argument(
        "--super-cheat",
        action="store_true",
        help="Execute the walkthrough directly (no agent, perfect play)"
    )

    args = parser.parse_args()

    # Handle --list-agents
    if args.list_agents:
        print(f"\nAvailable agent folders ({len(agent_folders)} total):\n")
        for folder in agent_folders:
            print(f"  {folder}/")
        print("\nEach folder must contain agent.py and mcp_server.py")
        print()
        sys.exit(0)

    # Handle --list-games
    if args.list_games:
        print(f"\nAvailable games ({len(available_games)} total):\n")
        # Print in columns
        cols = 5
        for i in range(0, len(available_games), cols):
            row = available_games[i:i+cols]
            print("  " + "  ".join(f"{g:<15}" for g in row))
        print()
        sys.exit(0)

    # Validate agent choice
    if args.agent not in agent_folders:
        print(f"\nError: Unknown agent folder '{args.agent}'")
        print(f"Available: {', '.join(agent_folders)}")
        print("Use --list-agents to see details.")
        sys.exit(1)

    # Validate game choice
    if args.game.lower() not in available_games:
        print(f"\nError: Unknown game '{args.game}'")
        print(f"Use --list-games to see {len(available_games)} available options.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Text Adventure MCP Agent Runner")
    print("=" * 60)
    if args.super_cheat:
        print("Mode: SUPER CHEAT (Execute Walkthrough)")
    else:
        print(f"Agent: {args.agent}/")
        if args.cheat:
            print("Cheat Mode: Enabled (walkthrough hints)")
    print(f"Game: {args.game}")
    print(f"Max Steps: {args.max_steps}")
    print(f"Verbose: {args.verbose}")

    # Run the agent (or super-cheat mode)
    try:
        if args.super_cheat:
            results = asyncio.run(run_walkthrough_cheat(args))
        else:
            results = asyncio.run(run_mcp_agent(args))

    except FileNotFoundError as e:
        print(f"\n[Error] {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n[Error] {e}")
        print("\nTo fix this:")
        print("1. Copy .env.example to .env")
        print("2. Add your HuggingFace token (HF_TOKEN)")
        sys.exit(1)
    except ImportError as e:
        print(f"\n[Import Error] {e}")
        print("\nMake sure to install dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    return results


if __name__ == "__main__":
    main()
