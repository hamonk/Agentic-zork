"""
Example: MCP ReAct Agent

A complete ReAct agent that uses MCP tools to play text adventure games.
This is a working example students can learn from.
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from visualization.logger import GameLogger

load_dotenv()

# =============================================================================
# LLM Configuration - DO NOT MODIFY
# =============================================================================

LLM_MODEL = "Qwen/Qwen2.5-72B-Instruct"

_hf_token = os.getenv("HF_TOKEN")
if not _hf_token:
    raise ValueError("HF_TOKEN not found. Set it in your .env file.")

LLM_CLIENT = InferenceClient(token=_hf_token)


def call_llm(prompt: str, system_prompt: str, seed: int, max_tokens: int = 300) -> str:
    """Call the LLM with the given prompt."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    
    response = LLM_CLIENT.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.0,
        max_tokens=max_tokens,
        seed=seed,
    )
    
    return response.choices[0].message.content


@dataclass
class RunResult:
    """Result of running the agent. Do not modify this class."""
    final_score: int
    max_score: int
    moves: int
    locations_visited: set[str]
    game_completed: bool
    error: Optional[str] = None
    history: list[tuple[str, str, str]] = field(default_factory=list)


# =============================================================================
# System Prompt
# =============================================================================

SYSTEM_PROMPT = """You are an expert text adventure game player. Your goal is to explore, collect treasures, and maximize your score.

AVAILABLE TOOLS (use these via MCP):
1. play_action - Execute game commands (north, take lamp, open mailbox, etc.)
2. memory - Get current game state, score, and recent history
3. get_map - See explored locations and connections
4. inventory - Check what you're carrying
5. get_valid_actions - Get list of valid actions at current location (USE THIS OFTEN!)

VALID GAME COMMANDS for play_action:
- Movement: north, south, east, west, up, down, enter, exit, ne, nw, se, sw
- Short forms: n, s, e, w, u, d
- Objects: take <item>, drop <item>, open <thing>, close <thing>, examine <thing>
- Light: turn on lamp, turn off lamp
- Interaction: push <thing>, pull <thing>, move <thing>, climb <thing>
- Combat: attack <enemy> with <weapon>
- Other: inventory, look, read <thing>, wait

FORBIDDEN (will NOT work): check, inspect, search, grab, use, help

RESPOND IN THIS EXACT FORMAT (no markdown):
THOUGHT: <brief reasoning about what to do next>
TOOL: <tool_name>
ARGS: <JSON arguments>

Examples:
THOUGHT: I need to see what's around me.
TOOL: play_action
ARGS: {"action": "look"}

THOUGHT: Let me check my current state and score.
TOOL: memory
ARGS: {}

THOUGHT: The mailbox might contain something useful.
TOOL: play_action
ARGS: {"action": "open mailbox"}

STRATEGY:
1. Use get_valid_actions to see what actions are possible at your current location
2. Start by checking inventory to see what you have
3. Explore SYSTEMATICALLY - try valid actions from get_valid_actions first
4. Use get_map frequently to track where you've been
5. Pick up useful items (lamp, torch, sword, keys, etc.)
6. Examine and interact with objects (open, push, pull, move, climb)
7. If stuck, call get_valid_actions to find new possibilities
8. Parse game responses carefully - they contain important clues
9. Don't repeat failed actions - learn from failures

DO NOT repeat the same action multiple times in a row."""


# =============================================================================
# Student Agent Implementation
# =============================================================================

class StudentAgent:
    """
    MCP ReAct Agent - A complete working example.
    
    This agent demonstrates:
    - ReAct loop (Thought -> Tool -> Observation)
    - Loop detection
    - Action validation
    - Score tracking via memory tool
    """
    
    def __init__(self, logger: Optional[GameLogger] = None, enable_logging: bool = True):
        """Initialize the agent state."""
        self.history: list[dict] = []
        self.recent_actions: list[str] = []
        self.score: int = 0
        self.failed_actions: dict[str, int] = {}  # Track failed actions to avoid repeating
        self.locations_explored: set[str] = set()  # Track visited locations
        self.unexplored_directions: list[str] = []  # Directions to try at current location
        self.steps_since_map_check: int = 0  # Track when we last checked the map
        self.steps_since_progress: int = 0  # Track steps without score/location change
        self.valid_actions: list[str] = []  # Valid actions at current location
        self.steps_since_valid_check: int = 0  # Track when we last checked valid actions
        self.current_map: Optional[str] = None  # Store map data for LLM context
        self.walkthrough_hints: Optional[list[str]] = None  # Optional walkthrough guidance
        
        # Auto-create logger if not provided and logging is enabled
        if logger is None and enable_logging:
            self.logger = GameLogger(log_dir="logs")
        else:
            self.logger = logger
        
        self.current_inventory: list[str] = []  # Track inventory for logging
    
    async def run(
        self,
        client,
        game: str,
        max_steps: int,
        seed: int,
        verbose: bool = False,
        walkthrough: Optional[list[str]] = None,
    ) -> RunResult:
        """Run the agent for a game session."""
        locations_visited = set()
        history = []
        moves = 0
        
        # Store walkthrough hints if provided
        self.walkthrough_hints = walkthrough
        
        # Initialize logging if logger provided
        if self.logger:
            self.logger.start_run(
                game=game,
                agent=self.__class__.__name__,
                seed=seed,
                max_steps=max_steps
            )
        
        # Get list of available tools
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        
        # Check inventory first to see what we start with
        inv_result = await client.call_tool("inventory", {})
        inv_text = self._extract_result(inv_result)
        self.current_inventory = self._parse_inventory(inv_text)
        if verbose:
            print(f"\n{inv_text}\n")
        
        # Show walkthrough info if provided (cheat mode)
        if self.walkthrough_hints:
            if verbose:
                print(f"\n[WALKTHROUGH MODE] You have access to {len(self.walkthrough_hints)} optimal steps\n")
        
        # Get valid actions at start
        try:
            valid_result = await client.call_tool("get_valid_actions", {})
            valid_text = self._extract_result(valid_result)
            if "Valid actions:" in valid_text:
                actions_str = valid_text.split("Valid actions:")[1].strip()
                self.valid_actions = [a.strip() for a in actions_str.split(",")]
            if verbose:
                print(f"\n{valid_text}\n")
        except Exception as e:
            if verbose:
                print(f"[INFO] Could not get valid actions: {e}")
        
        # Get initial observation
        result = await client.call_tool("play_action", {"action": "look"})
        observation = self._extract_result(result)
        
        # Track initial location
        location = self._extract_location(observation)
        locations_visited.add(location)
        self.locations_explored.add(location)
        
        # Initialize unexplored directions
        self.unexplored_directions = ["north", "south", "east", "west", "up", "down"]
        
        if verbose:
            print(f"\n{observation}")

        # Main ReAct loop
        for step in range(1, max_steps + 1):
            # Strategic tool usage: check map periodically and when stuck
            self.steps_since_map_check += 1
            if self.steps_since_map_check >= 5 or self.steps_since_progress > 3:
                map_result = await client.call_tool("get_map", {})
                map_text = self._extract_result(map_result)
                self.current_map = map_text  # Store for LLM prompt
                if verbose:
                    print(f"\n[MAP CHECK]\n{map_text}\n")
                self.steps_since_map_check = 0
            
            # Check valid actions when entering new location or stuck
            self.steps_since_valid_check += 1
            if self.steps_since_valid_check >= 4 or self.steps_since_progress > 2:
                try:
                    valid_result = await client.call_tool("get_valid_actions", {})
                    valid_text = self._extract_result(valid_result)
                    if "Valid actions:" in valid_text:
                        actions_str = valid_text.split("Valid actions:")[1].strip()
                        self.valid_actions = [a.strip() for a in actions_str.split(",")]
                        if verbose:
                            print(f"\n[VALID ACTIONS]\n{valid_text}\n")
                    self.steps_since_valid_check = 0
                except Exception as e:
                    if verbose:
                        print(f"[INFO] Could not get valid actions: {e}")
            
            # Build prompt with context (include exploration hints)
            prompt = self._build_prompt(observation)
            
            # Call LLM for reasoning (use step-based seed for variety)
            response = call_llm(prompt, SYSTEM_PROMPT, seed + step)
            
            # Parse the response
            thought, tool_name, tool_args = self._parse_response(response, tool_names)
            
            if verbose:
                print(f"\n--- Step {step} ---")
                print(f"[THOUGHT] {thought}")
                print(f"[TOOL] {tool_name}({tool_args})")
            
            # Validate and fix common issues
            tool_name, tool_args = self._validate_tool_call(tool_name, tool_args, tool_names)
            
            # Enhanced loop and stuck detection
            if tool_name == "play_action":
                action = tool_args.get("action", "look")
                self.recent_actions.append(action)
                if len(self.recent_actions) > 5:
                    self.recent_actions = self.recent_actions[-5:]
                
                # Detect loops - if same action 3 times, try something different
                if len(self.recent_actions) >= 3 and len(set(self.recent_actions[-3:])) == 1:
                    if verbose:
                        print(f"[WARNING] Loop detected - trying different action")
                    
                    # Try valid action that we haven't tried yet
                    if self.valid_actions:
                        for valid_action in self.valid_actions:
                            if valid_action not in self.recent_actions[-5:] and valid_action not in self.failed_actions:
                                tool_args = {"action": valid_action}
                                if verbose:
                                    print(f"[UNSTUCK] Trying valid action: {valid_action}")
                                break
                        else:
                            # No untried valid actions, try unexplored direction
                            if self.unexplored_directions:
                                new_action = self.unexplored_directions.pop(0)
                                tool_args = {"action": new_action}
                                if verbose:
                                    print(f"[UNSTUCK] Trying direction: {new_action}")
                            else:
                                tool_args = {"action": "look"}
                    elif self.unexplored_directions:
                        new_action = self.unexplored_directions.pop(0)
                        tool_args = {"action": new_action}
                        if verbose:
                            print(f"[UNSTUCK] Trying direction: {new_action}")
                    else:
                        tool_args = {"action": "look"}
                    self.recent_actions.append(tool_args["action"])
                
                moves += 1
            
            # Execute the tool
            try:
                result = await client.call_tool(tool_name, tool_args)
                observation = self._extract_result(result)
                
                # Update inventory if it's an inventory check
                if tool_name == "inventory":
                    self.current_inventory = self._parse_inventory(observation)
                
                if verbose:
                    print(f"[RESULT] {observation[:200]}...")
            except Exception as e:
                observation = f"Error: {e}"
                if verbose:
                    print(f"[ERROR] {e}")
            
            # Track location and detect progress
            new_location = self._extract_location(observation)
            old_score = self.score
            self._update_score(observation)
            
            # Check for progress (new location or score increase)
            if new_location != location or self.score > old_score:
                self.steps_since_progress = 0
                
                # New location: reset unexplored directions and get valid actions
                if new_location != location:
                    location = new_location
                    locations_visited.add(location)
                    if location not in self.locations_explored:
                        self.locations_explored.add(location)
                        self.unexplored_directions = ["north", "south", "east", "west", "up", "down"]
                        self.steps_since_valid_check = 999  # Force valid actions check on next iteration
                        if verbose:
                            print(f"[NEW LOCATION] {location}")
            else:
                self.steps_since_progress += 1
                
                # Track failed actions
                if tool_name == "play_action":
                    action = tool_args.get("action", "look")
                    # Check if action failed (common failure phrases)
                failure_phrases = ["can't", "cannot", "don't", "not", "fail", "impossible", 
                                   "doesn't work", "not allowed", "not know which way", 
                                   "get in big trouble", "look dark"]
                if any(phrase in observation.lower() for phrase in failure_phrases):
                    self.failed_actions[action] = self.failed_actions.get(action, 0) + 1
                    if verbose and self.failed_actions[action] >= 2:
                        print(f"[WARNING] '{action}' has failed {self.failed_actions[action]} times - avoiding")
            if verbose:
                print(f"[LOCATION] {location} | Score: {self.score} | Progress: {self.steps_since_progress} steps")
            
            # Update history
            self.history.append({
                "step": step,
                "thought": thought,
                "tool": tool_name,
                "args": tool_args,
                "result": observation[:200],
                "location": location,
                "score": self.score
            })
            
            # Structured logging
            if self.logger:
                self.logger.log_step(
                    step=step,
                    thought=thought,
                    tool=tool_name,
                    tool_args=tool_args,
                    result=observation,
                    location=location,
                    score=self.score,
                    moves=moves,
                    inventory=self.current_inventory.copy(),
                    valid_actions=self.valid_actions.copy()
                )
            # Truncate history to last 10 entries to save memory
            if len(self.history) > 10:
                self.history = self.history[-10:]
            
            # Track score from observation
            self._update_score(observation)
            
            # Record in result history
            history.append((thought, f"{tool_name}({tool_args})", observation[:100]))
            
            # Check for game over
            if self._is_game_over(observation):
                if verbose:
                    print("\n*** GAME OVER ***")
                break
        
        # Finalize logging
        if self.logger:
            # Get final map state
            map_state = {}
            for loc, exits in getattr(self, '_map_connections', {}).items():
                map_state[loc] = list(exits)
            
            log_path = self.logger.end_run(
                final_score=self.score,
                final_moves=moves,
                locations_visited=list(locations_visited),
                game_completed=self._is_game_over(observation),
                map_state=map_state
            )
            if verbose:
                print(f"\n[LOG SAVED] {log_path}")
        
        return RunResult(
            final_score=self.score,
            max_score=350,
            moves=moves,
            locations_visited=locations_visited,
            game_completed=self._is_game_over(observation),
            history=history,
        )
    
    def _build_prompt(self, observation: str) -> str:
        """Build the prompt for the LLM with context."""
        parts = []
        
        parts.append(f"Current Score: {self.score}")
        parts.append(f"Locations explored: {len(self.locations_explored)}")
        
        # Show walkthrough hint if available (next optimal step)
        if self.walkthrough_hints and len(self.history) < len(self.walkthrough_hints):
            current_step = len(self.history)
            next_hint = self.walkthrough_hints[current_step]
            # Show next 2-3 steps as hints
            upcoming = self.walkthrough_hints[current_step:current_step+3]
            parts.append(f"\n[HINT - Optimal next steps: {', '.join(upcoming)}]")
        
        # Recent history
        if self.history:
            parts.append("\nRecent actions:")
            # take last 3 entries
            for entry in self.history[-3:]:
                # Show tool calls with arguments and truncated results
                action = entry.get("args", {}).get("action", entry["tool"])
                result_short = entry["result"][:80] + "..." if len(entry["result"]) > 80 else entry["result"]
                loc = entry.get("location", "?")
                score_diff = f" (+{entry['score'] - self.history[self.history.index(entry)-1]['score']}pts)" if entry.get('score', 0) > (self.history[self.history.index(entry)-1]['score'] if self.history.index(entry) > 0 else 0) else ""
                parts.append(f"  > {action} @ {loc}{score_diff} -> {result_short}")
            
            # Warn about repeated actions
            if self.recent_actions and len(set(self.recent_actions[-3:])) == 1:
                parts.append(f"\n[WARNING: You've been doing '{self.recent_actions[-1]}' repeatedly. TRY SOMETHING DIFFERENT!]")
        
        # Show failed actions to avoid
        if self.failed_actions:
            failed_list = [f"'{k}' ({v}x)" for k, v in self.failed_actions.items() if v >= 2]
            if failed_list:
                parts.append(f"\n[AVOID: These actions have failed: {', '.join(failed_list)}]")
        
        # Show valid actions if available
        if self.valid_actions:
            parts.append(f"\n[VALID ACTIONS: {', '.join(self.valid_actions[:15])}]")
        
        # Show map summary when stuck to help with navigation
        if self.steps_since_progress > 3 and self.current_map:
            # Extract just location count and a few recent locations
            map_lines = self.current_map.split('\n')
            location_count = sum(1 for line in map_lines if line.strip().startswith('*'))
            parts.append(f"\n[MAP: {location_count} locations explored. Consider calling get_map tool for full details.]")
        
        # Show unexplored directions if stuck
        if self.steps_since_progress > 2 and self.unexplored_directions:
            parts.append(f"\n[HINT: Try unexplored directions: {', '.join(self.unexplored_directions[:3])}]")
        
        parts.append(f"\nCurrent situation:\n{observation}")
        parts.append("\nWhat do you do next?")
        
        return "\n".join(parts)
    
    def _parse_response(self, response: str, valid_tools: list[str]) -> tuple[str, str, dict]:
        """Parse the LLM response to extract thought, tool, and arguments."""
        thought = "No reasoning provided"
        tool_name = "play_action"
        tool_args = {"action": "look"}
        
        lines = response.strip().split("\n")
        
        for line in lines:
            line_clean = line.strip()
            line_upper = line_clean.upper()
            
            if line_upper.startswith("THOUGHT:"):
                thought = line_clean.split(":", 1)[1].strip()
            
            elif line_upper.startswith("TOOL:"):
                raw_tool = line_clean.split(":", 1)[1].strip().lower()
                raw_tool = raw_tool.replace("**", "").replace("*", "").replace("`", "")
                raw_tool = raw_tool.split()[0] if raw_tool else "play_action"
                tool_name = raw_tool
            
            elif line_upper.startswith("ARGS:"):
                args_part = line_clean.split(":", 1)[1].strip()
                try:
                    args_part = args_part.replace("'", '"')
                    tool_args = json.loads(args_part)
                except json.JSONDecodeError:
                    match = re.search(r'"action"\s*:\s*"([^"]+)"', args_part)
                    if match:
                        tool_args = {"action": match.group(1)}
                    else:
                        tool_args = {"action": "look"}
        
        return thought, tool_name, tool_args
    
    def _validate_tool_call(self, tool_name: str, tool_args: dict, valid_tools: list[str]) -> tuple[str, dict]:
        """Validate and fix common tool call issues."""
        # Fix tool name
        if tool_name not in valid_tools:
            if tool_name in ["action", "do", "command"]:
                tool_name = "play_action"
            elif tool_name in ["map", "location"]:
                tool_name = "get_map"
            elif tool_name in ["mem", "state", "status"]:
                tool_name = "memory"
            elif tool_name in ["inv", "items"]:
                tool_name = "inventory"
            else:
                tool_name = "play_action"
        
        # Fix action verbs
        if tool_name == "play_action":
            action = tool_args.get("action", "look")
            
            invalid_verb_map = {
                "check": "examine",
                "inspect": "examine",
                "search": "look",
                "grab": "take",
                "pick": "take",
                "use": "examine",
                "investigate": "examine",
            }
            
            words = action.lower().split()
            if words and words[0] in invalid_verb_map:
                words[0] = invalid_verb_map[words[0]]
                action = " ".join(words)
            
            action = action.lower().strip()
            action = action.replace("**", "").replace("*", "").replace("`", "")
            action = " ".join(action.split())
            
            # Avoid actions that have failed multiple times
            if action in self.failed_actions and self.failed_actions[action] >= 3:
                # Try a valid action or unexplored direction instead
                if self.valid_actions:
                    for valid_action in self.valid_actions:
                        if valid_action not in self.failed_actions:
                            action = valid_action
                            break
                elif self.unexplored_directions:
                    action = self.unexplored_directions.pop(0)
            
            # Track direction attempts and remove from unexplored
            direction_variants = {
                "north": ["north", "n"], "south": ["south", "s"],
                "east": ["east", "e"], "west": ["west", "w"],
                "up": ["up", "u"], "down": ["down", "d"]
            }
            for direction, variants in direction_variants.items():
                if action in variants and direction in self.unexplored_directions:
                    self.unexplored_directions.remove(direction)
            
            tool_args["action"] = action
        
        return tool_name, tool_args
    
    def _extract_result(self, result) -> str:
        """Extract text from MCP tool result."""
        if hasattr(result, 'content') and result.content:
            return result.content[0].text
        if isinstance(result, list) and result:
            return result[0].text if hasattr(result[0], 'text') else str(result[0])
        return str(result)
    
    def _extract_location(self, observation: str) -> str:
        """Extract location name from observation."""
        if not observation:
            return "Unknown"
        lines = observation.strip().split('\n')
        # First non-empty line is usually the location
        for line in lines:
            line = line.strip()
            if line and not line.startswith('['):
                return line
        return "Unknown"
    
    def _update_score(self, text: str) -> None:
        """Update score from game text."""
        patterns = [
            r'Score:\s*(\d+)',
            r'score[:\s]+(\d+)',
            r'\[Score:\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.score = max(self.score, int(match.group(1)))
    
    def _is_game_over(self, text: str) -> bool:
        """Check if the game is over."""
        game_over_phrases = [
            "game over",
            "you have died",
            "you are dead",
            "*** you have died ***",
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in game_over_phrases)
    
    def _parse_inventory(self, inv_text: str) -> list[str]:
        """Parse inventory text into list of items."""
        if "empty-handed" in inv_text.lower() or "nothing" in inv_text.lower():
            return []
        
        # Extract items after "Inventory:" or similar
        items = []
        if ":" in inv_text:
            items_str = inv_text.split(":", 1)[1].strip()
            items = [item.strip() for item in items_str.split(",") if item.strip()]
        
        return items


# =============================================================================
# Local Testing
# =============================================================================

async def test_agent():
    """Test the agent locally."""
    from fastmcp import Client
    
    # Initialize logger
    logger = GameLogger(log_dir="logs")
    agent = StudentAgent(logger=logger)
    
    async with Client("mcp_server.py") as client:
        result = await agent.run(
            client=client,
            game="zork1",
            max_steps=20,
            seed=42,
            verbose=True,
        )
        
        print(f"\n{'=' * 50}")
        print(f"Final Score: {result.final_score}")
        print(f"Moves: {result.moves}")
        print(f"Locations: {len(result.locations_visited)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_agent())
