"""
Example: MCP Server for Text Adventures

A complete MCP server that exposes text adventure games via tools.
This demonstrates a full-featured server with memory, mapping, and inventory.
Includes structured logging of all game events.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import games module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from games.zork_env import TextAdventureEnv, list_available_games


# Get game from environment variable (default: zork1)
INITIAL_GAME = os.environ.get("GAME", "zork1")

# Create the MCP server
mcp = FastMCP("Text Adventure Server")


class GameState:
    """Manages the text adventure game state and exploration data."""
    
    def __init__(self, game: str = "zork1", enable_logging: bool = True):
        self.game_name = game
        self.env = TextAdventureEnv(game)
        self.state = self.env.reset()
        self.history: list[tuple[str, str]] = []
        self.explored_locations: dict[str, set[str]] = {}
        self.current_location: str = self._extract_location(self.state.observation)
        
        # Server-side event logging
        self.enable_logging = enable_logging
        self.event_log: list[dict] = []
        self.log_dir = Path("logs/server_events")
        if enable_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._log_event("session_start", {"game": game})
    
    def _extract_location(self, observation: str) -> str:
        """Extract location name from observation (usually first line)."""
        lines = observation.strip().split('\n')
        return lines[0] if lines else "Unknown"
    
    def _log_event(self, event_type: str, data: dict):
        """Log a server event."""
        if not self.enable_logging:
            return
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data,
            "location": self.current_location,
            "score": self.state.score,
            "moves": self.state.moves
        }
        self.event_log.append(event)
    
    def save_event_log(self):
        """Save event log to file."""
        if not self.enable_logging or not self.event_log:
            return
        
        filename = f"{self.game_name}_server_{self.session_id}.json"
        filepath = self.log_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump({
                "game": self.game_name,
                "session_id": self.session_id,
                "total_moves": self.state.moves,
                "final_score": self.state.score,
                "events": self.event_log
            }, f, indent=2)
        
        return str(filepath)
    
    def take_action(self, action: str) -> str:
        """Execute a game action and return the result."""
        old_location = self.current_location
        old_score = self.state.score
        
        self.state = self.env.step(action)
        result = self.state.observation
        
        # Track history
        self.history.append((action, result))
        if len(self.history) > 50:
            self.history = self.history[-50:]
        
        # Update map
        new_location = self._extract_location(result)
        if action in ["north", "south", "east", "west", "up", "down", 
                      "enter", "exit", "n", "s", "e", "w", "u", "d"]:
            if self.current_location not in self.explored_locations:
                self.explored_locations[self.current_location] = set()
            if new_location != self.current_location:
                self.explored_locations[self.current_location].add(f"{action} -> {new_location}")
        self.current_location = new_location
        
        # Log event
        self._log_event("action", {
            "action": action,
            "old_location": old_location,
            "new_location": new_location,
            "location_changed": old_location != new_location,
            "reward": self.state.reward,
            "score_change": self.state.score - old_score,
            "result_preview": result[:100]
        })
        
        return result
    
    def get_memory(self) -> str:
        """Get a summary of current game state."""
        recent = self.history[-5:] if self.history else []
        recent_str = "\n".join([f"  > {a} -> {r[:60]}..." for a, r in recent]) if recent else "  (none yet)"
        
        self._log_event("memory_check", {
            "locations_explored": len(self.explored_locations)
        })
        
        return f"""Current State:
- Location: {self.current_location}
- Score: {self.state.score} points
- Moves: {self.state.moves}
- Game: {self.game_name}

Recent Actions:
{recent_str}

Current Observation:
{self.state.observation}"""
    
    def get_map(self) -> str:
        """Get a map of explored locations."""
        self._log_event("map_check", {
            "locations_count": len(self.explored_locations)
        })
        
        if not self.explored_locations:
            return "Map: No locations explored yet. Try moving around!"
        
        lines = ["Explored Locations and Exits:"]
        for loc, exits in sorted(self.explored_locations.items()):
            lines.append(f"\n* {loc}")
            for exit_info in sorted(exits):
                lines.append(f"    -> {exit_info}")
        
        lines.append(f"\n[Current] {self.current_location}")
        return "\n".join(lines)
    
    def get_inventory(self) -> str:
        """Get current inventory."""
        items = self.state.inventory if hasattr(self.state, 'inventory') and self.state.inventory else []
        
        item_names = []
        if items:
            for item in items:
                item_str = str(item)
                item_lower = item_str.lower()
                if "parent" in item_lower:
                    idx = item_lower.index("parent")
                    name = item_str[:idx].strip()
                    if ":" in name:
                        name = name.split(":", 1)[1].strip()
                    item_names.append(name)
                elif ":" in item_str:
                    name = item_str.split(":")[1].strip()
                    item_names.append(name)
                else:
                    item_names.append(item_str)
        
        self._log_event("inventory_check", {
            "item_count": len(item_names),
            "items": item_names
        })
        
        if not items:
            return "Inventory: You are empty-handed."
        
        return f"Inventory: {', '.join(item_names)}"


# Global game state
_game_state: GameState | None = None


def get_game() -> GameState:
    """Get or initialize the game state."""
    global _game_state
    if _game_state is None:
        _game_state = GameState(INITIAL_GAME)
    return _game_state


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool()
def play_action(action: str) -> str:
    """
    Execute a game action in the text adventure.
    
    Args:
        action: The command to execute (e.g., 'north', 'take lamp', 'open mailbox')
    
    Returns:
        The game's response to your action
    """
    game = get_game()
    result = game.take_action(action)
    
    # Add score info
    score_info = f"\n\n[Score: {game.state.score} | Moves: {game.state.moves}]"
    
    if game.state.reward > 0:
        score_info = f"\n\n+{game.state.reward} points! (Total: {game.state.score})"
    
    done_info = ""
    if game.state.done:
        done_info = "\n\nGAME OVER"
        # Save server event log when game ends
        log_path = game.save_event_log()
        if log_path:
            done_info += f"\n[Server log saved: {log_path}]"
    
    return result + score_info + done_info


@mcp.tool()
def memory() -> str:
    """
    Get a summary of the current game state.
    
    Returns location, score, moves, recent actions, and current observation.
    """
    return get_game().get_memory()


@mcp.tool()
def get_map() -> str:
    """
    Get a map showing explored locations and connections.
    
    Useful for navigation and avoiding getting lost.
    """
    return get_game().get_map()


@mcp.tool()
def inventory() -> str:
    """
    Check what items you are currently carrying.
    """
    return get_game().get_inventory()


@mcp.tool()
def get_valid_actions() -> str:
    """
    Get a list of likely valid actions from the current location.
    
    Returns:
        List of actions that might work here
    """
    # This is a hint: Jericho provides get_valid_actions()
    game = get_game()
    if game.env and game.env.env:
        valid = game.env.env.get_valid_actions()
        game._log_event("valid_actions_check", {
            "action_count": len(valid),
            "actions": valid[:20]
        })
        return "Valid actions: " + ", ".join(valid[:20])
    return "Could not determine valid actions"

# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    mcp.run(show_banner=False)
