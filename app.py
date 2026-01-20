"""
Gradio App - Text Adventure AI Agent Assignment

A simple interface for the text adventure AI agent assignment.
"""

import gradio as gr

TITLE = "Playing Zork has never been so boring"

DESCRIPTION = """
In this assignment, you will build an AI Agent and an MCP server to play text adventure games like Zork.

The evaluation server is not ready yet, but you can look at the templates by cloning this repository.
"""

CLONE_INSTRUCTIONS = """
## Getting Started

### 1. Clone the Repository

```bash
git clone https://huggingface.co/spaces/LLM-course/Agentic-zork
cd Agentic-zork
```

### 2. Set Up Environment

```bash
# Create virtual environment (using uv recommended)
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

### 3. Configure API Token

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your HuggingFace token
# HF_TOKEN=hf_your_token_here
```

Get your HuggingFace token at: https://huggingface.co/settings/tokens

### 4. Explore the Templates

The templates are in the `templates/` folder:

- `mcp_server_template.py` - MCP server starter code
- `react_agent_template.py` - ReAct agent starter code

### 5. Test Your Implementation

```bash
# Run your agent
python run_agent.py --mode mcp -n 20

# List available games (57 total!)
python run_agent.py --list-games
```

## Resources

- [Assignment Instructions](templates/README.md)
- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Protocol](https://modelcontextprotocol.io/)
"""

demo = gr.Blocks(title=TITLE)

with demo:
    gr.Markdown(f"# {TITLE}")
    gr.Markdown(DESCRIPTION)
    gr.Markdown("---")
    gr.Markdown(CLONE_INSTRUCTIONS)

if __name__ == "__main__":
    demo.launch()
