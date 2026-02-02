---
title: Text Adventure Agent Submission
emoji: "\U0001F5FA"
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: "5.0.0"
app_file: app.py
pinned: false
license: mit
---

# Text Adventure Agent Submission

## Overview

This is my submission for the Text Adventure Agent assignment. My agent uses the ReAct pattern to play text adventure games via MCP.

## Approach

<!-- Describe your approach here -->

- What strategy does your agent use?
- What tools did you implement in your MCP server?
- Any interesting techniques or optimizations?

## Files

| File | Description |
|------|-------------|
| `agent.py` | ReAct agent with `StudentAgent` class |
| `mcp_server.py` | MCP server with game interaction tools |
| `app.py` | Gradio interface for HF Space |
| `requirements.txt` | Additional dependencies |

## How to Submit

1. Fork the template Space: `https://huggingface.co/spaces/LLM-course/text-adventure-template`
2. Clone your fork locally
3. Implement your agent in `agent.py` and `mcp_server.py`
4. Test locally (see below)
5. Push your changes to your Space
6. Submit your Space URL on the course platform

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Test the MCP server interactively
fastmcp dev mcp_server.py

# Run your agent on a game
python run_agent.py --agent . --game lostpig -v -n 20

# Run evaluation
python -m evaluation.evaluate -s . -g lostpig -t 3
```
