# MCP Server Documentation

## Overview

The MCP (Model Context Protocol) server (`mcp_server.py`) is a FastMCP-based server that exposes text adventure games through a set of tools. It acts as the interface between the agent and the Jericho/Z-machine game environment, providing structured access to game actions and state information.

## Architecture

### Core Components

1. **FastMCP Server Instance**: The main server that handles MCP protocol communication
2. **GameState Class**: Manages game environment, state tracking, and exploration data
3. **MCP Tools**: Four exposed tools that agents can call to interact with the game
4. **Game Environment**: Wrapper around Jericho's Z-machine interpreter

## Server Initialization

```python
mcp = FastMCP("Text Adventure Server")
INITIAL_GAME = os.environ.get("GAME", "zork1")
```

- The server reads the game to load from the `GAME` environment variable
- Defaults to `zork1` if not specified
- The runner (`run_agent.py`) sets this environment variable when launching the server subprocess

## GameState Class

The `GameState` class is the heart of the server, managing all game-related state and operations.

### Initialization

```python
def __init__(self, game: str = "zork1"):
```

When a `GameState` is created:
1. Stores the game name
2. Creates a `TextAdventureEnv` instance from the `games.zork_env` module
3. Resets the environment to get initial state
4. Initializes tracking structures:
   - `history`: List of (action, result) tuples (max 50 entries)
   - `explored_locations`: Dict mapping locations to their discovered exits
   - `current_location`: Extracted from the initial observation

### Key Methods

#### `_extract_location(observation: str) -> str`

**Purpose**: Parse location name from game observation text

**How it works**:
- Splits observation into lines
- Returns the first line (Infocom games typically put location names on the first line)
- Returns "Unknown" if no lines are found

**Example**:
```
Input: "West of House\nYou are standing in an open field..."
Output: "West of House"
```

#### `take_action(action: str) -> str`

**Purpose**: Execute a game action and update state tracking

**Flow**:
1. Calls `env.step(action)` to execute action in the Jericho environment
2. Gets the observation result
3. Appends (action, result) to history
4. Truncates history to last 50 entries if needed
5. Updates the exploration map if the action was a movement command
6. Updates current_location
7. Returns the observation

**Map Update Logic**:
- Only tracks movement commands (north, south, east, west, up, down, enter, exit, and abbreviated versions)
- If the action causes a location change, records the exit: `"north -> Kitchen"`
- Builds a directed graph of explored locations

**Example Flow**:
```
Action: "north"
→ env.step("north")
→ Result: "Kitchen\nYou are in a kitchen..."
→ History: [(...previous...), ("north", "Kitchen\nYou are...")]
→ Map: {"West of House": {"north -> Kitchen"}}
→ current_location: "Kitchen"
```

#### `get_memory() -> str`

**Purpose**: Provide a formatted summary of current game state

**Returns a string containing**:
1. Current location
2. Score and moves count
3. Game name
4. Last 5 actions with truncated results (60 chars)
5. Full current observation

**Example Output**:
```
Current State:
- Location: West of House
- Score: 0 points
- Moves: 3
- Game: zork1

Recent Actions:
  > look -> West of House You are standing in an open field west ...
  > open mailbox -> Opening the small mailbox reveals a leaflet....
  > take leaflet -> Taken....

Current Observation:
West of House
You are standing in an open field west of a white house...
```

**Use Case**: The agent calls this to get context about where it is and what it has done recently. This information is incorporated into the LLM prompt.

#### `get_map() -> str`

**Purpose**: Generate a visual representation of explored locations and their connections

**Returns**:
- If no locations explored: a hint message
- Otherwise: A formatted list of locations with their exits
- Marks the current location with `[Current]`

**Example Output**:
```
Explored Locations and Exits:

* Kitchen
    -> east -> Living Room
    -> south -> West of House

* West of House
    -> east -> Behind House
    -> north -> Kitchen

[Current] Kitchen
```

**Use Case**: Helps the agent navigate, avoid getting lost, and plan exploration systematically.

#### `get_inventory() -> str`

**Purpose**: Get a human-readable list of items the player is carrying

**Processing Logic**:
The raw inventory data from Jericho can be complex object representations. This method:
1. Checks if `state.inventory` exists and has items
2. Parses each item to extract just the name:
   - Removes "parent" references
   - Strips prefixes before colons
   - Cleans up the string representation
3. Returns a comma-separated list

**Example**:
```
Raw: [Object:52 (brass lantern) parent=Object:191]
Cleaned: "brass lantern"
Output: "Inventory: brass lantern, rusty knife, leaflet"
```

**Use Case**: Agent needs to know what tools it has available for puzzles and challenges.

## Global State Management

```python
_game_state: GameState | None = None

def get_game() -> GameState:
    global _game_state
    if _game_state is None:
        _game_state = GameState(INITIAL_GAME)
    return _game_state
```

**Pattern**: Singleton pattern
- Ensures only one game instance per server process
- Lazy initialization on first tool call
- All tools share the same game state

**Why this matters**: The runner launches the MCP server as a subprocess. Each subprocess gets its own game instance, allowing multiple agents to run different games in parallel.

## MCP Tools

The server exposes four tools that agents can invoke via MCP protocol. Each tool is decorated with `@mcp.tool()` which registers it with the FastMCP server.

### 1. `play_action(action: str) -> str`

**Purpose**: Execute any game command

**Parameters**:
- `action` (str): The command to execute (e.g., "north", "take lamp", "open mailbox")

**Returns**: The game's text response plus scoring information

**Processing**:
1. Gets the game state
2. Executes the action via `game.take_action()`
3. Appends score and moves information
4. Adds reward info if points were gained
5. Adds "GAME OVER" if the game ended

**Example Call**:
```python
await client.call_tool("play_action", {"action": "take lamp"})
```

**Example Response**:
```
Taken.

+5 points! (Total: 5)

[Score: 5 | Moves: 4]
```

**This is the primary interaction tool** - everything the agent does in the game goes through this.

### 2. `memory() -> str`

**Purpose**: Get a summary of current game state

**Parameters**: None

**Returns**: Formatted state summary (see `get_memory()` method above)

**Use Case**: Agent calls this to get context before deciding next action. The example agent uses this in its ReAct loop to inform the LLM prompt.

**Example Call**:
```python
await client.call_tool("memory", {})
```

### 3. `get_map() -> str`

**Purpose**: Get exploration map

**Parameters**: None

**Returns**: Formatted location graph (see `get_map()` method above)

**Use Case**: Navigation assistance, avoiding revisiting locations unnecessarily, planning systematic exploration.

**Example Call**:
```python
await client.call_tool("get_map", {})
```

### 4. `inventory() -> str`

**Purpose**: Check carried items

**Parameters**: None

**Returns**: Comma-separated list of items or "empty-handed" message

**Use Case**: Check available tools, verify items were picked up, manage carrying capacity.

**Example Call**:
```python
await client.call_tool("inventory", {})
```

## Execution Flow

### Server Startup

1. The runner executes: `python example_submission/mcp_server.py`
2. Server imports dependencies and creates the FastMCP instance
3. Server registers all `@mcp.tool()` decorated functions
4. `mcp.run()` starts the stdio transport (reads from stdin, writes to stdout)
5. Server waits for MCP protocol messages

### Agent Connection

1. Runner creates a `fastmcp.Client` with `StdioTransport` pointing to the server subprocess
2. Client sends `initialize` message
3. Server responds with capabilities and tool list
4. Client can now invoke tools

### Tool Invocation Flow

```
Agent → Client.call_tool("play_action", {"action": "north"})
  → MCP Protocol Message (JSON-RPC over stdio)
    → Server receives and routes to play_action()
      → get_game() returns singleton GameState
        → game.take_action("north")
          → env.step("north")
            → Jericho Z-machine interpreter
              → Returns observation
            → Update history and map
          → Format response with score
        → Return to server
      → Server sends MCP response
    → Client receives result
  → Agent processes observation
```

### State Persistence

**Within a session**: State persists in the `_game_state` singleton
**Between sessions**: State is NOT persisted - each run starts fresh

**Implications**:
- An agent can make multiple tool calls and the game remembers
- Restarting the server resets the game
- Perfect for evaluation (deterministic starting conditions)

## Integration with Agent

The agent in `agent.py` uses this server through the FastMCP client:

```python
# Agent code
result = await client.call_tool("play_action", {"action": "look"})
observation = result.content[0].text
```

The agent doesn't need to know how the server works internally - it just:
1. Calls tools by name
2. Passes arguments as a dict
3. Receives structured results

## Design Patterns

### 1. Facade Pattern
The `GameState` class provides a simplified interface to the complex Jericho environment.

### 2. Singleton Pattern
Only one game instance per server process via `get_game()`.

### 3. Decorator Pattern
`@mcp.tool()` decorators register functions as MCP tools without modifying their core logic.

### 4. Adapter Pattern
The server adapts Jericho's Z-machine interface to the MCP protocol, allowing any MCP client to play text adventures.

## Error Handling

The current implementation has minimal error handling:
- If a game action fails, Jericho returns an error message (e.g., "I don't understand that")
- The server passes this through to the agent
- The agent is responsible for handling invalid commands

**Potential improvements**:
- Validate actions before calling `env.step()`
- Catch exceptions and return structured error messages
- Add retry logic for transient failures

## Performance Considerations

1. **History Truncation**: Limited to 50 entries to prevent memory growth
2. **Location Extraction**: Simple string split (fast)
3. **Inventory Parsing**: String manipulation (could be optimized with regex)
4. **State Persistence**: In-memory only (fast but not persistent)

## Extension Points

Students can enhance this server by adding:
1. **More Tools**: Save/load game state, hints, walkthrough mode
2. **Advanced Mapping**: Detect loops, suggest unexplored areas
3. **Object Tracking**: Track seen objects and their locations
4. **Goal Detection**: Identify treasures, objectives, puzzles
5. **Action Validation**: Pre-validate actions before execution
6. **State Serialization**: Save/restore game progress

## Debugging

To test the server interactively:

```bash
fastmcp dev example_submission/mcp_server.py
```

This opens an MCP inspector where you can manually call tools and see responses.

## Security Considerations

- The server has full access to the file system (via Python)
- Actions are limited to Jericho game commands (can't execute arbitrary code)
- No network access required
- Safe for local execution and HuggingFace Spaces deployment

## Summary

The MCP server is a **stateful adapter** that:
- Wraps Jericho game environments
- Exposes game interactions through four MCP tools
- Tracks exploration history and mapping
- Provides formatted state summaries
- Enables agent-game communication via MCP protocol

Its design prioritizes:
- **Simplicity**: Easy for students to understand and modify
- **Completeness**: Provides all necessary tools for game playing
- **Extensibility**: Clear extension points for enhancements
- **Determinism**: Reproducible runs for evaluation
