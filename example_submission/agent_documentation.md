# Agent Documentation

## Overview

The agent (`agent.py`) implements a complete ReAct (Reasoning + Acting) agent that plays text adventure games using an LLM (Large Language Model) and MCP (Model Context Protocol) tools. It demonstrates the ReAct pattern: the LLM generates thoughts and actions, executes them via MCP tools, observes results, and iterates.

## Architecture

### Core Components

1. **LLM Interface**: Calls to HuggingFace Inference API
2. **StudentAgent Class**: Main agent logic implementing the ReAct loop
3. **Response Parser**: Extracts structured actions from LLM text responses
4. **State Tracking**: History, loop detection, score monitoring
5. **Tool Validation**: Fixes common LLM mistakes

## LLM Configuration

### Model and Client Setup

```python
LLM_MODEL = "Qwen/Qwen2.5-72B-Instruct"
LLM_CLIENT = InferenceClient(token=_hf_token)
```

**Model Choice**: Qwen2.5-72B-Instruct
- Large model (72B parameters) with strong instruction-following
- Free tier available via HuggingFace Inference API
- Good at structured output formats

**Why this matters**: The model must follow the exact THOUGHT/TOOL/ARGS format. Larger models are more reliable at this.

### `call_llm()` Function

```python
def call_llm(prompt: str, system_prompt: str, seed: int, max_tokens: int = 300) -> str
```

**Purpose**: Centralized LLM calling with deterministic configuration

**Parameters**:
- `prompt`: The user message (current game situation)
- `system_prompt`: Instructions on how to behave and format responses
- `seed`: Random seed for deterministic output
- `max_tokens`: Maximum response length (default 300)

**Critical Settings**:
```python
temperature=0.0  # Deterministic (no randomness)
seed=seed        # Reproducible results
```

**Why deterministic?**: For fair evaluation across submissions. Same seed + same situation = same response.

**Message Format**:
```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt},
]
```

This is the standard chat format - system sets behavior, user provides context.

**Returns**: The LLM's text response (which should follow THOUGHT/TOOL/ARGS format)

## RunResult Dataclass

```python
@dataclass
class RunResult:
    final_score: int
    max_score: int
    moves: int
    locations_visited: set[str]
    game_completed: bool
    error: Optional[str] = None
    history: list[tuple[str, str, str]] = field(default_factory=list)
```

**Purpose**: Structured return value from `agent.run()`

**Fields**:
- `final_score`: Points achieved in the game
- `max_score`: Maximum possible points (350 for Zork I)
- `moves`: Number of game actions executed
- `locations_visited`: Set of unique location names seen
- `game_completed`: Whether game reached an ending
- `error`: Error message if run failed (None if successful)
- `history`: Complete audit log of (thought, tool_call, observation) tuples

**Used by**: `run_agent.py` for display and `evaluate.py` for metrics calculation

## System Prompt

The system prompt is the agent's "instructions manual" - it tells the LLM:

### 1. Role and Goal

```
You are an expert text adventure game player.
Your goal is to explore, collect treasures, and maximize your score.
```

Sets the context and objective.

### 2. Available Tools

Lists the four MCP tools with brief descriptions:
- `play_action`: Execute game commands
- `memory`: Get current state summary
- `get_map`: See explored locations
- `inventory`: Check carried items

**Why list tools here?**: The LLM needs to know what actions are possible.

### 3. Valid Game Commands

Provides a vocabulary of working commands:
```
Movement: north, south, east, west, up, down, enter, exit
Objects: take <item>, drop <item>, open <thing>, examine <thing>
Light: turn on lamp, turn off lamp
Combat: attack <enemy> with <weapon>
Other: inventory, look, read <thing>, wait
```

**Critical**: Also lists FORBIDDEN commands that don't work:
```
FORBIDDEN (will NOT work): check, inspect, search, grab, use, help
```

**Why?**: LLMs often generate natural language actions that seem reasonable but don't work in Infocom games. Pre-training the prompt reduces these errors.

### 4. Response Format

```
RESPOND IN THIS EXACT FORMAT (no markdown):
THOUGHT: <brief reasoning about what to do next>
TOOL: <tool_name>
ARGS: <JSON arguments>
```

**Provides examples** of correctly formatted responses.

**Why this format?**: 
- Easy to parse with regex
- Separates reasoning (THOUGHT) from action (TOOL/ARGS)
- Follows ReAct pattern from the paper
- JSON args are unambiguous

### 5. Strategy Guidelines

Provides high-level playing advice:
```
1. Start by looking around and checking memory
2. Explore systematically - try all directions
3. Pick up useful items (lamp, sword, etc.)
4. Open containers (mailbox, window, etc.)
5. Use get_map to avoid getting lost
6. Turn on lamp before dark areas!
```

**Why include strategy?**: The LLM doesn't know how to play text adventures. These hints improve performance.

### 6. Anti-Loop Instruction

```
DO NOT repeat the same action multiple times in a row.
```

Helps prevent the most common failure mode.

## StudentAgent Class

The main agent implementation with state tracking and the ReAct loop.

### Instance Variables

```python
def __init__(self):
    self.history: list[dict] = []
    self.recent_actions: list[str] = []
    self.score: int = 0
```

**`self.history`**: Dict-based working memory
- Stores last 10 steps with full details
- Used to build LLM prompts
- Format: `{"step": int, "thought": str, "tool": str, "args": dict, "result": str}`
- Truncated to prevent prompt from growing too long

**`self.recent_actions`**: List of last 5 action strings
- Used for loop detection
- Only tracks `play_action` calls
- Rolling window (last 5)

**`self.score`**: Current game score
- Extracted from observations
- Tracked separately for easy access

### Main Method: `async def run()`

This is the entry point called by the runner.

**Signature**:
```python
async def run(
    self,
    client,           # FastMCP client connected to mcp_server.py
    game: str,        # Game name (e.g., "zork1")
    max_steps: int,   # Maximum ReAct iterations
    seed: int,        # Random seed for determinism
    verbose: bool = False,  # Print progress
) -> RunResult:
```

**Flow Overview**:
1. Initialize tracking variables
2. Get list of available tools from server
3. Get initial observation ("look")
4. Main loop (up to `max_steps` iterations):
   - Build prompt with context
   - Call LLM for reasoning
   - Parse response
   - Validate and fix tool call
   - Detect loops
   - Execute tool
   - Update state tracking
   - Check for game over
5. Return `RunResult`

### Detailed Execution Flow

#### 1. Setup Phase

```python
locations_visited = set()  # Track unique locations (for metrics)
history = []               # Audit log (returned in RunResult)
moves = 0                  # Count of play_action calls

# Get available tools
tools = await client.list_tools()
tool_names = [t.name for t in tools]  # e.g., ["play_action", "memory", "get_map", "inventory"]
```

**Why get tool names?**: Used for validation - the LLM might hallucinate tool names, so we need the authoritative list.

#### 2. Initial Observation

```python
result = await client.call_tool("play_action", {"action": "look"})
observation = self._extract_result(result)
```

**Why start with "look"?**: Games typically show location description on start. This gives the agent context before the first LLM call.

**Location tracking**:
```python
location = observation.split("\n")[0] if observation else "Unknown"
locations_visited.add(location)
```

Assumes first line is location name (standard for Infocom games).

#### 3. Main ReAct Loop

```python
for step in range(1, max_steps + 1):
```

**Loop structure**: Fixed iteration count (not condition-based)
- Prevents infinite loops
- Ensures evaluation fairness (same max steps for all agents)
- Breaks early if game ends

**Step 1: Build Prompt**
```python
prompt = self._build_prompt(observation)
```

Constructs the user message with:
- Current score
- Recent action history (last 3)
- Loop warnings if detected
- Current observation
- "What do you do next?"

More details in `_build_prompt()` section below.

**Step 2: LLM Call**
```python
response = call_llm(prompt, SYSTEM_PROMPT, seed + step)
```

**Key detail**: `seed + step` means each iteration uses a different seed
- Prevents the agent from being too deterministic across steps
- Still reproducible (same seed parameter → same sequence)
- Allows variation in behavior

**Step 3: Parse Response**
```python
thought, tool_name, tool_args = self._parse_response(response, tool_names)
```

Extracts structured data from LLM's text response. See `_parse_response()` section.

**Step 4: Verbose Output**
```python
if verbose:
    print(f"\n--- Step {step} ---")
    print(f"[THOUGHT] {thought}")
    print(f"[TOOL] {tool_name}({tool_args})")
```

Shows agent's reasoning in real-time (useful for debugging).

**Step 5: Validation**
```python
tool_name, tool_args = self._validate_tool_call(tool_name, tool_args, tool_names)
```

Fixes common LLM mistakes. See `_validate_tool_call()` section.

**Step 6: Loop Detection**
```python
if tool_name == "play_action":
    action = tool_args.get("action", "look")
    self.recent_actions.append(action)
    if len(self.recent_actions) > 5:
        self.recent_actions = self.recent_actions[-5:]
    
    # Detect loops - if same action 3 times, force "look"
    if len(self.recent_actions) >= 3 and len(set(self.recent_actions[-3:])) == 1:
        if verbose:
            print(f"[WARNING] Loop detected - forcing 'look'")
        tool_args = {"action": "look"}
        self.recent_actions.append("look")
    
    moves += 1
```

**Loop detection logic**:
- Track last 5 actions
- If last 3 are identical → agent is stuck
- Force "look" to break the loop
- Increment move counter

**Why this works**: "look" refreshes the observation and might give the LLM different context to reason about.

**Step 7: Tool Execution**
```python
try:
    result = await client.call_tool(tool_name, tool_args)
    observation = self._extract_result(result)
    
    if verbose:
        print(f"[RESULT] {observation[:200]}...")
except Exception as e:
    observation = f"Error: {e}"
    if verbose:
        print(f"[ERROR] {e}")
```

**Error handling**: If tool call fails, set observation to error message. Agent continues (doesn't crash).

**Step 8: State Updates**
```python
# Update location tracking
location = observation.split("\n")[0] if observation else "Unknown"
locations_visited.add(location)

# Update working memory (self.history)
self.history.append({
    "step": step,
    "thought": thought,
    "tool": tool_name,
    "args": tool_args,
    "result": observation[:200]  # Truncated to save memory
})
if len(self.history) > 10:
    self.history = self.history[-10:]

# Update score
self._update_score(observation)

# Update audit log (local history variable)
history.append((thought, f"{tool_name}({tool_args})", observation[:100]))
```

**Two histories**:
1. `self.history` (instance var): Working memory for prompt building, last 10 entries, full details
2. `history` (local var): Complete audit log for return value, all entries, simplified tuples

**Step 9: Game Over Check**
```python
if self._is_game_over(observation):
    if verbose:
        print("\n*** GAME OVER ***")
    break
```

Exits loop early if game ended.

#### 4. Return Results

```python
return RunResult(
    final_score=self.score,
    max_score=350,
    moves=moves,
    locations_visited=locations_visited,
    game_completed=self._is_game_over(observation),
    history=history,
)
```

## Helper Methods

### `_build_prompt(observation: str) -> str`

**Purpose**: Construct the user message for the LLM with current context

**Structure**:
```
Current Score: 15

Recent actions:
  > north -> Kitchen You are in a kitchen...
  > take knife -> Taken....
  > south -> West of House You are standing...

[WARNING: You've been doing 'north' repeatedly. TRY SOMETHING DIFFERENT!]

Current situation:
West of House
You are standing in an open field west of a white house...

What do you do next?
```

**Components**:

1. **Score**: Motivates the agent to maximize points
2. **Recent actions** (last 3 from `self.history`):
   - Shows what the agent just did
   - Truncates results to 80 chars
   - Prevents repeating recent actions
3. **Loop warning**: If same action repeated 3x
4. **Current situation**: Full latest observation
5. **Prompt**: "What do you do next?"

**Why this structure?**:
- Provides immediate context (recent history)
- Doesn't overload prompt (only last 3 actions)
- Warns about loops explicitly
- Ends with clear question

### `_parse_response(response: str, valid_tools: list[str]) -> tuple[str, str, dict]`

**Purpose**: Extract structured data from LLM's text response

**Expected format**:
```
THOUGHT: I should explore to the north.
TOOL: play_action
ARGS: {"action": "north"}
```

**Parsing logic**:

1. **Initialize defaults**:
```python
thought = "No reasoning provided"
tool_name = "play_action"
tool_args = {"action": "look"}
```
If parsing fails, these safe defaults are used.

2. **Line-by-line parsing**:
```python
for line in lines:
    line_clean = line.strip()
    line_upper = line_clean.upper()
```

3. **Extract THOUGHT**:
```python
if line_upper.startswith("THOUGHT:"):
    thought = line_clean.split(":", 1)[1].strip()
```
Split on first colon, take everything after.

4. **Extract TOOL**:
```python
elif line_upper.startswith("TOOL:"):
    raw_tool = line_clean.split(":", 1)[1].strip().lower()
    raw_tool = raw_tool.replace("**", "").replace("*", "").replace("`", "")
    raw_tool = raw_tool.split()[0] if raw_tool else "play_action"
    tool_name = raw_tool
```

**Cleaning steps**:
- Convert to lowercase (tool names are lowercase)
- Remove markdown formatting (`**`, `*`, `` ` ``)
- Take only first word (handles "play_action with args" type errors)

5. **Extract ARGS**:
```python
elif line_upper.startswith("ARGS:"):
    args_part = line_clean.split(":", 1)[1].strip()
    try:
        args_part = args_part.replace("'", '"')  # Fix single quotes
        tool_args = json.loads(args_part)
    except json.JSONDecodeError:
        # Fallback: regex search for "action": "value"
        match = re.search(r'"action"\s*:\s*"([^"]+)"', args_part)
        if match:
            tool_args = {"action": match.group(1)}
```

**Robust parsing**:
- Try JSON parsing first
- Fix common issue: single quotes → double quotes
- If JSON fails, use regex to extract action
- Falls back to safe default if all fails

**Why this complexity?**: LLMs don't always produce perfect JSON. This parser handles common mistakes gracefully.

### `_validate_tool_call(tool_name: str, tool_args: dict, valid_tools: list[str]) -> tuple[str, dict]`

**Purpose**: Fix common LLM mistakes in tool calls

**Part 1: Fix tool name**
```python
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
        tool_name = "play_action"  # Safe default
```

**Common mistakes**:
- LLM uses "action" instead of "play_action"
- Uses abbreviations ("inv" for inventory)
- Hallucinates tool names

**Part 2: Fix action verbs**
```python
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
```

**Why?**: LLMs generate natural language commands that don't work in Infocom parsers:
- "check lamp" → "examine lamp"
- "grab sword" → "take sword"
- "search room" → "look"

**Part 3: Clean action string**
```python
action = action.lower().strip()
action = action.replace("**", "").replace("*", "").replace("`", "")
action = " ".join(action.split())  # Normalize whitespace
tool_args["action"] = action
```

Removes markdown formatting and normalizes spaces.

### `_extract_result(result) -> str`

**Purpose**: Extract text from MCP tool result

MCP results can have different structures:
```python
if hasattr(result, 'content') and result.content:
    return result.content[0].text
if isinstance(result, list) and result:
    return result[0].text if hasattr(result[0], 'text') else str(result[0])
return str(result)
```

Handles various response formats from the MCP client.

### `_update_score(text: str) -> None`

**Purpose**: Extract and update score from game text

**Patterns tried**:
```python
patterns = [
    r'Score:\s*(\d+)',       # "Score: 15"
    r'score[:\s]+(\d+)',     # "score 15" or "score: 15"
    r'\[Score:\s*(\d+)',     # "[Score: 15"
]
```

**Logic**:
```python
for pattern in patterns:
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        self.score = max(self.score, int(match.group(1)))
```

Uses `max()` to ensure score never decreases (handles repeated observations).

### `_is_game_over(text: str) -> bool`

**Purpose**: Detect if game has ended

**Phrases checked**:
```python
game_over_phrases = [
    "game over",
    "you have died",
    "you are dead",
    "*** you have died ***",
]
```

**Logic**: Case-insensitive substring search

**Limitation**: Only detects death, not victory. Could be enhanced to detect winning conditions.

## Local Testing

The file includes a test function for development:

```python
async def test_agent():
    from fastmcp import Client
    
    agent = StudentAgent()
    
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
```

**Usage**:
```bash
cd example_submission
python agent.py
```

**What this does**:
1. Creates FastMCP client pointing to `mcp_server.py`
2. Runs agent for 20 steps
3. Prints results

**Note**: This is different from using `run_agent.py`. Here the agent directly manages the MCP server subprocess.

## Design Patterns

### 1. ReAct Pattern (Reason + Act)
```
Observe → Think → Act → Observe → Think → Act → ...
```

The core loop alternates between reasoning (LLM call) and acting (tool execution).

### 2. Template Method Pattern
The `run()` method defines the algorithm structure, with helper methods (`_parse_response`, `_validate_tool_call`, etc.) implementing specific steps.

### 3. Adapter Pattern
`_extract_result()` adapts various MCP result formats to a uniform string.

### 4. Strategy Pattern
The system prompt defines the "strategy" for playing games, which could be swapped for different approaches.

### 5. State Pattern
`self.history` and `self.recent_actions` maintain agent state across loop iterations.

## Error Handling Strategy

**Graceful degradation**:
- Invalid tool calls → fixed automatically
- JSON parsing errors → regex fallback
- Tool execution errors → continue with error message
- Loop detection → force safe action

**Philosophy**: Keep running even when things go wrong. Better to do something than crash.

## Performance Considerations

1. **LLM Latency**: Each step waits for LLM response (~1-3 seconds)
2. **History Truncation**: Prevents prompt from growing indefinitely
3. **Seed Variation**: `seed + step` provides variety without full randomness
4. **Max Tokens**: Limited to 300 to speed up responses

## Extension Points

Students can enhance the agent by:

1. **Better Prompting**: More examples, better strategy instructions
2. **Memory Management**: Summarize old history instead of truncating
3. **Planning**: Multi-step reasoning before acting
4. **State Modeling**: Build internal world model
5. **Goal-Directed**: Set subgoals (find lamp, reach treasure room, etc.)
6. **Learning**: Adapt strategy based on success/failure
7. **Multi-Tool Calls**: Check inventory before actions, use map for navigation

## Evaluation Integration

The `run_agent.py` script calls this agent:

```python
agent = StudentAgent()
async with Client(server_path) as client:
    result = await agent.run(client, game, max_steps, seed, verbose)
```

The returned `RunResult` is used for:
- Console output (score, moves, locations)
- Metrics calculation (evaluation/metrics.py)
- Leaderboard ranking

## HuggingFace Spaces Deployment

When deployed to HF Spaces:
1. The Gradio UI (app.py) collects parameters
2. Calls `agent.run()` asynchronously
3. Streams verbose output to the UI
4. Displays final `RunResult`

The agent code works identically in local and deployed environments.

## Security Considerations

- **API Key**: HF_TOKEN must be set (loaded from .env locally, Spaces secrets in deployment)
- **LLM Safety**: Model outputs are parsed but not executed as code (only as game commands)
- **Resource Limits**: max_steps prevents runaway loops, max_tokens limits LLM cost
- **Determinism**: seed parameter ensures reproducibility

## Debugging Tips

1. **Enable verbose**: See step-by-step reasoning
2. **Print prompts**: Add `print(prompt)` before `call_llm()`
3. **Check parsing**: Add prints in `_parse_response()`
4. **Test parsing**: Create test cases with malformed responses
5. **Use breakpoints**: Set breakpoints in the loop
6. **Check history**: Inspect `self.history` at each step

## Common Issues and Solutions

### Issue: Agent repeats same action
**Solution**: Loop detection forces "look" after 3 repetitions

### Issue: LLM generates invalid tool names
**Solution**: `_validate_tool_call()` maps to valid names

### Issue: Agent uses forbidden verbs
**Solution**: `invalid_verb_map` translates to working verbs

### Issue: JSON parsing fails
**Solution**: Regex fallback in `_parse_response()`

### Issue: Prompt gets too long
**Solution**: History truncated to last 10 entries

### Issue: Score not updating
**Solution**: Multiple regex patterns in `_update_score()`

## Summary

The agent is a **ReAct loop** that:
- Uses an LLM to reason about game state
- Calls MCP tools to interact with the game
- Tracks history and detects loops
- Validates and fixes common LLM errors
- Returns structured results for evaluation

Its design emphasizes:
- **Robustness**: Handles LLM mistakes gracefully
- **Determinism**: Seeded for reproducible evaluation
- **Clarity**: Well-structured for student learning
- **Extensibility**: Clear points for enhancement
