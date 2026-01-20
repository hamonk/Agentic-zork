"""
ReAct Agent Template for Text Adventure Games

This is a starter template for building a ReAct agent that plays text adventures using MCP.

ReAct (Reasoning + Acting) is a simple but effective agent pattern:
1. THINK: Reason about the current situation
2. ACT: Choose and execute a tool
3. OBSERVE: See the result
4. Repeat until goal is achieved

Your task is to implement:
1. Connect to the MCP server
2. Implement the ReAct loop
3. Use the LLM to generate thoughts and choose actions

TODO:
1. Set up the MCP client connection
2. Implement the agent loop
3. Parse LLM responses to extract tool calls
"""

import asyncio
import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# FastMCP client for connecting to MCP servers
from fastmcp import Client


# =============================================================================
# Configuration
# =============================================================================

# Load environment variables
load_dotenv()

# LLM Configuration
MODEL = os.getenv("HF_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN not found. Set it in your .env file.")


# =============================================================================
# System Prompt - Instructions for the LLM
# =============================================================================

SYSTEM_PROMPT = """You are playing a classic text adventure game.

GOAL: Explore the world, solve puzzles, collect treasures, and maximize your score.

AVAILABLE TOOLS:
- play_action: Execute a game command (north, take lamp, open mailbox, etc.)
- memory: Get current game state summary (optional, if implemented)
- get_map: See explored locations (optional, if implemented)
- inventory: Check your items (optional, if implemented)

VALID GAME COMMANDS:
- Movement: north, south, east, west, up, down
- Objects: take <item>, drop <item>, open <thing>, examine <thing>
- Light: turn on lamp

RESPOND IN THIS EXACT FORMAT:
THOUGHT: <your reasoning>
TOOL: <tool_name>
ARGS: <arguments as JSON, or empty {} if no args>

Example:
THOUGHT: I see a container. I should open it to see what's inside.
TOOL: play_action
ARGS: {"action": "open container"}
"""


# =============================================================================
# ReAct Agent Class
# =============================================================================

class ReActAgent:
    """
    A ReAct agent that uses MCP tools to play text adventures.
    
    TODO: Complete this implementation!
    """
    
    def __init__(self, mcp_server_path: str):
        """
        Initialize the agent.
        
        Args:
            mcp_server_path: Path to the MCP server script
        """
        self.mcp_server_path = mcp_server_path
        self.llm = InferenceClient(token=HF_TOKEN)
        self.history: list[dict] = []
    
    async def run(self, max_steps: int = 50, verbose: bool = True):
        """
        Run the ReAct agent loop.
        
        TODO: Implement the main agent loop!
        
        Steps:
        1. Connect to MCP server using FastMCP Client
        2. Get initial observation (call play_action with "look")
        3. Loop:
           a. Build prompt with current observation
           b. Call LLM to get thought and tool choice
           c. Parse the response
           d. Execute the chosen tool via MCP
           e. Update history with observation
           f. Check if done
        """
        # TODO: Implement the agent loop
        # Hint: Use `async with Client(self.mcp_server_path) as client:`
        
        print("=" * 60)
        print("Starting Text Adventure ReAct Agent")
        print("=" * 60)
        
        # Connect to the MCP server
        async with Client(self.mcp_server_path) as client:
            # List available tools
            tools = await client.list_tools()
            print(f"\nAvailable tools: {[t.name for t in tools]}")
            
            # Get initial observation
            result = await client.call_tool("play_action", {"action": "look"})
            observation = result.content[0].text
            print(f"\nInitial observation:\n{observation}\n")
            
            # Main loop
            for step in range(1, max_steps + 1):
                print(f"\n{'─' * 40}")
                print(f"Step {step}")
                print("─" * 40)
                
                # TODO: Build prompt for LLM
                prompt = self._build_prompt(observation)
                
                # TODO: Call LLM
                response = self._call_llm(prompt)
                
                # TODO: Parse response to get tool and arguments
                thought, tool_name, tool_args = self._parse_response(response)
                
                if verbose:
                    print(f"\nTHOUGHT: {thought}")
                    print(f"TOOL: {tool_name}")
                    print(f"ARGS: {tool_args}")
                
                # TODO: Execute the tool via MCP
                try:
                    result = await client.call_tool(tool_name, tool_args)
                    observation = result.content[0].text
                    print(f"\nRESULT:\n{observation}")
                except Exception as e:
                    observation = f"Error: {e}"
                    print(f"\nERROR: {e}")
                
                # TODO: Update history
                self.history.append({
                    "thought": thought,
                    "tool": tool_name,
                    "args": tool_args,
                    "result": observation
                })
                
                # Check for game over
                if "GAME OVER" in observation.upper():
                    print("\n\nGame Over!")
                    break
        
        print("\n" + "=" * 60)
        print("Agent finished")
        print("=" * 60)
    
    def _build_prompt(self, observation: str) -> str:
        """
        Build the prompt for the LLM.
        
        TODO: Customize this to include relevant context!
        
        Consider including:
        - Current observation
        - Recent history (last few actions and results)
        - Warnings about repeated actions
        """
        parts = []
        
        # Add recent history (last 3 actions)
        if self.history:
            parts.append("Recent actions:")
            for entry in self.history[-3:]:
                parts.append(f"  > {entry['tool']}({entry['args']}) -> {entry['result'][:100]}...")
            parts.append("")
        
        # Current observation
        parts.append(f"Current observation:\n{observation}")
        parts.append("\nWhat do you do next?")
        
        return "\n".join(parts)
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM to get the next action.
        
        TODO: Customize LLM parameters if needed.
        """
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=200,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM Error: {e}")
            return "THOUGHT: Error occurred.\nTOOL: play_action\nARGS: {\"action\": \"look\"}"
    
    def _parse_response(self, response: str) -> tuple[str, str, dict]:
        """
        Parse the LLM response to extract thought, tool, and arguments.
        
        TODO: Make this more robust!
        
        Expected format:
        THOUGHT: <reasoning>
        TOOL: <tool_name>
        ARGS: <json args>
        """
        import json
        
        thought = ""
        tool_name = "play_action"
        tool_args = {"action": "look"}
        
        lines = response.strip().split("\n")
        
        for line in lines:
            line_upper = line.upper().strip()
            
            if line_upper.startswith("THOUGHT:"):
                thought = line.split(":", 1)[1].strip()
            elif line_upper.startswith("TOOL:"):
                tool_name = line.split(":", 1)[1].strip().lower()
            elif line_upper.startswith("ARGS:"):
                try:
                    args_str = line.split(":", 1)[1].strip()
                    tool_args = json.loads(args_str)
                except (json.JSONDecodeError, IndexError):
                    # Try to extract action from malformed args
                    if "action" in args_str.lower():
                        # Simple extraction for common case
                        tool_args = {"action": "look"}
        
        return thought, tool_name, tool_args


# =============================================================================
# Main - Run the agent
# =============================================================================

async def main():
    """Run the ReAct agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the ReAct Text Adventure Agent")
    parser.add_argument(
        "--server", "-s",
        default="templates/mcp_server_template.py",
        help="Path to the MCP server script"
    )
    parser.add_argument(
        "--max-steps", "-n",
        type=int,
        default=50,
        help="Maximum steps to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    agent = ReActAgent(args.server)
    await agent.run(max_steps=args.max_steps, verbose=args.verbose)


if __name__ == "__main__":
    asyncio.run(main())
