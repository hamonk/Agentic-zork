# Text Adventure LLM Agent Templates

This folder contains starter templates for building your own AI agent to play text adventure games.

## Assignment Overview

You need to implement two components:

1. **MCP Server** (`mcp_server_template.py`) - Exposes game functionality as tools
2. **ReAct Agent** (`react_agent_template.py`) - Uses the MCP server to play the game

## Architecture

```
+-------------------+     MCP Protocol     +------------------+
|                   | <------------------> |                  |
|   ReAct Agent     |    (tools/calls)     |   MCP Server     |
|   (Your Agent)    |                      |   (Your Server)  |
|                   |                      |                  |
+-------------------+                      +------------------+
        |                                           |
        | LLM API                                   | Game API
        v                                           v
+-------------------+                      +------------------+
|                   |                      |                  |
|   HuggingFace     |                      |  Text Adventure  |
|   Inference API   |                      |   (Jericho)      |
+-------------------+                      +------------------+
```

## Getting Started

### 1. Set Up Environment

```bash
# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Copy environment file and add your HuggingFace token
cp .env.example .env
# Edit .env and add HF_TOKEN=your_token_here
```

### 2. Implement the MCP Server

Start with `mcp_server_template.py`. Your server needs to:

1. Create a FastMCP server instance
2. Implement at least the `play_action` tool to send commands to the game
3. Optionally add helper tools (memory, map, inventory, hints)

Test your server:
```bash
# Run the server directly (will use stdio transport)
python templates/mcp_server_template.py

# Or use FastMCP's development tools
fastmcp dev templates/mcp_server_template.py
```

### 3. Implement the ReAct Agent

Start with `react_agent_template.py`. Your agent needs to:

1. Connect to your MCP server using FastMCP Client
2. Implement a ReAct loop (Thought -> Action -> Observation)
3. Use the LLM to decide what tools to call
4. Parse the LLM's response and execute the chosen tool

Test your agent:
```bash
python templates/react_agent_template.py
```

## MCP Protocol Basics

MCP (Model Context Protocol) is a standard for LLM-tool communication:

- **Tools**: Functions the LLM can call (e.g., `play_action`, `get_inventory`)
- **Resources**: Read-only data (e.g., game state, map)
- **Prompts**: Reusable prompt templates

FastMCP makes it easy:

```python
# Server side - define a tool
from fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool()
def my_tool(arg: str) -> str:
    """Tool description for the LLM."""
    return f"Result: {arg}"

# Client side - call a tool
from fastmcp import Client

async with Client(mcp) as client:
    result = await client.call_tool("my_tool", {"arg": "hello"})
```

## Evaluation Criteria

Your implementation will be evaluated on:

1. **Correctness**: Does it work? Can it play text adventure games?
2. **Score**: How many points does your agent achieve?
3. **Code Quality**: Is your code clean, documented, and well-structured?
4. **Creativity**: Did you add interesting features or optimizations?

## Tips

1. Start simple - get a basic loop working first
2. Use `memory()` and `get_map()` tools to help the agent track state
3. Add loop detection to avoid repeating the same actions
4. Test with verbose output to debug the agent's reasoning
5. The LLM may generate invalid commands - handle errors gracefully

## Resources

- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Jericho (Text Adventures)](https://github.com/microsoft/jericho)
- [HuggingFace Inference API](https://huggingface.co/docs/huggingface_hub/guides/inference)
