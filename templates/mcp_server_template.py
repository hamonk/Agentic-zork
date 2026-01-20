"""
MCP Server Template for Text Adventure Games

This is a starter template for building your text adventure MCP server.
Your task is to implement the tools that allow an AI agent to play text adventures.

FastMCP makes it easy to create MCP servers - just decorate functions!

TODO:
1. Implement the play_action tool (required)
2. Add helper tools like memory, get_map, inventory (recommended)
3. Test your server with: fastmcp dev templates/mcp_server_template.py
"""

import sys
import os

# Add parent directory to path to import games module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from games.zork_env import TextAdventureEnv


# =============================================================================
# Create the MCP Server
# =============================================================================

# TODO: Create a FastMCP server instance
# Hint: mcp = FastMCP("Your Server Name")
mcp = FastMCP("Text Adventure Server")


# =============================================================================
# Game State Management
# =============================================================================

class GameState:
    """
    Manages the text adventure game state.
    
    TODO: You may want to extend this class to track:
    - Action history (for context)
    - Explored locations (for mapping)
    - Current location name
    """
    
    def __init__(self, game: str = "zork1"):
        self.game_name = game
        self.env = TextAdventureEnv(game)
        self.state = self.env.reset()
        # TODO: Add more state tracking here
        # self.history = []
        # self.explored_locations = {}
    
    def take_action(self, action: str) -> str:
        """Execute a game action and return the result."""
        self.state = self.env.step(action)
        # TODO: Update your state tracking here
        return self.state.observation


# Global game instance (created on first use)
_game: GameState | None = None


def get_game() -> GameState:
    """Get or create the game instance."""
    global _game
    if _game is None:
        _game = GameState()
    return _game


# =============================================================================
# MCP Tools - IMPLEMENT THESE!
# =============================================================================

@mcp.tool()
def play_action(action: str) -> str:
    """
    Execute a game action in the text adventure.
    
    This is the main tool for interacting with the game.
    
    Common commands:
    - Movement: north, south, east, west, up, down
    - Objects: take <item>, drop <item>, open <thing>
    - Look: look, examine <thing>
    
    Args:
        action: The command to execute (e.g., 'north', 'take lamp')
    
    Returns:
        The game's response to your action
    """
    # TODO: Implement this tool
    # Hint: Use get_game().take_action(action)
    game = get_game()
    result = game.take_action(action)
    
    # TODO: Optionally add score info or game over detection
    return result


# TODO: Implement additional helper tools
# These are optional but will help your agent play better!

# @mcp.tool()
# def memory() -> str:
#     """
#     Get a summary of the current game state.
#     
#     Returns location, score, recent actions, and current observation.
#     Use this to understand where you are and what happened recently.
#     """
#     # TODO: Implement this
#     pass


# @mcp.tool()
# def get_map() -> str:
#     """
#     Get a map of explored locations.
#     
#     Useful for navigation and avoiding getting lost.
#     """
#     # TODO: Implement this
#     pass


# @mcp.tool()
# def inventory() -> str:
#     """
#     Check what items you are carrying.
#     """
#     # TODO: Implement this
#     pass


# =============================================================================
# Main - Run the server
# =============================================================================

if __name__ == "__main__":
    # This runs the server using stdio transport (for local testing)
    mcp.run()
