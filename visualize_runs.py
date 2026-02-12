"""
Gradio UI for visualizing game run logs.

Provides interactive visualization of agent gameplay including:
- Score progression over time
- Location exploration graph
- Step-by-step replay with thought/action/result
- Valid actions and inventory tracking
"""

import gradio as gr
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import networkx as nx
from pathlib import Path
from typing import Optional

from visualization.logger import GameRunLog


def load_log_file(file_path: str) -> Optional[GameRunLog]:
    """Load a game log from file."""
    try:
        return GameRunLog.load(file_path)
    except Exception as e:
        print(f"Error loading log: {e}")
        return None


def create_score_chart(log: GameRunLog) -> go.Figure:
    """Create score progression chart."""
    if not log.steps:
        return go.Figure().add_annotation(text="No data available")
    
    steps = [s.step for s in log.steps]
    scores = [s.score for s in log.steps]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=steps,
        y=scores,
        mode='lines+markers',
        name='Score',
        line=dict(color='#2ecc71', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title=f"Score Progression - {log.game}",
        xaxis_title="Step",
        yaxis_title="Score",
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig


def create_location_graph(log: GameRunLog) -> go.Figure:
    """Create network graph of explored locations."""
    if not log.map_state:
        return go.Figure().add_annotation(text="No map data available")
    
    # Build graph
    G = nx.DiGraph()
    
    # Add nodes and edges from map_state
    for location, exits in log.map_state.items():
        G.add_node(location)
        for exit_info in exits:
            # Parse "direction -> destination"
            if " -> " in exit_info:
                _, destination = exit_info.split(" -> ", 1)
                G.add_edge(location, destination)
    
    # If no map_state, build from steps
    if not G.nodes():
        for step in log.steps:
            G.add_node(step.location)
        
        for i in range(len(log.steps) - 1):
            if log.steps[i].location != log.steps[i+1].location:
                G.add_edge(log.steps[i].location, log.steps[i+1].location)
    
    # Layout
    try:
        pos = nx.spring_layout(G, seed=42, k=2, iterations=50)
    except:
        pos = {node: (i, 0) for i, node in enumerate(G.nodes())}
    
    # Create edge traces
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#95a5a6'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Create node traces
    node_x = []
    node_y = []
    node_text = []
    node_size = []
    
    # Count visits to each location
    visit_counts = {}
    for step in log.steps:
        visit_counts[step.location] = visit_counts.get(step.location, 0) + 1
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"{node}<br>Visits: {visit_counts.get(node, 0)}")
        node_size.append(20 + visit_counts.get(node, 0) * 5)
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[node.split()[0] for node in G.nodes()],  # Shortened labels
        hovertext=node_text,
        textposition="top center",
        marker=dict(
            size=node_size,
            color='#3498db',
            line=dict(width=2, color='white')
        )
    )
    
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title="Location Exploration Map",
        showlegend=False,
        hovermode='closest',
        template='plotly_white',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
    
    return fig


def create_moves_chart(log: GameRunLog) -> go.Figure:
    """Create moves per step chart."""
    if not log.steps:
        return go.Figure().add_annotation(text="No data available")
    
    steps = [s.step for s in log.steps]
    moves = [s.moves for s in log.steps]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=steps,
        y=moves,
        mode='lines',
        fill='tozeroy',
        name='Moves',
        line=dict(color='#e74c3c', width=2)
    ))
    
    fig.update_layout(
        title="Moves Over Time",
        xaxis_title="Step",
        yaxis_title="Total Moves",
        template='plotly_white'
    )
    
    return fig


def format_step_details(log: GameRunLog, step_num: int) -> str:
    """Format detailed information for a specific step."""
    if not log.steps or step_num < 1 or step_num > len(log.steps):
        return "No step selected"
    
    step = log.steps[step_num - 1]
    
    # Get the action taken
    action_taken = step.tool_args.get('action', step.tool) if step.tool == 'play_action' else step.tool
    
    details = f"""## Step {step.step} / {len(log.steps)}

**🤔 Agent Thought:** {step.thought}

**🎯 Action:** `{action_taken}`

**📊 State:** {step.location} | Score: {step.score} | Moves: {step.moves} | Inv: {', '.join(step.inventory) if step.inventory else 'Empty'}

**✅ Valid Actions:** {', '.join(step.valid_actions[:10]) if step.valid_actions else 'None'}{'...' if step.valid_actions and len(step.valid_actions) > 10 else ''}

**👀 Game Response:**
```
{step.result}
```
"""
    return details


def create_summary_stats(log: GameRunLog) -> str:
    """Create summary statistics."""
    return f"""## Run Summary

**Game:** {log.game}  
**Agent:** {log.agent}  
**Seed:** {log.seed}  

**Final Score:** {log.final_score}  
**Total Moves:** {log.final_moves}  
**Total Steps:** {len(log.steps)}  
**Locations Visited:** {len(log.locations_visited)}  
**Completed:** {'✅ Yes' if log.game_completed else '❌ No'}

**Duration:** {log.start_time} to {log.end_time or 'In progress'}
"""


def load_and_visualize(log_filepath):
    """Load log file and create all visualizations."""
    if not log_filepath:
        return (
            "Please select a log file",
            "No step selected",
            gr.Slider(maximum=100, value=1)
        )
    
    log = load_log_file(log_filepath)
    if not log:
        return (
            "Error loading log file",
            "Error loading log",
            gr.Slider(maximum=100, value=1)
        )
    
    summary = create_summary_stats(log)
    
    # First step details
    step_details = format_step_details(log, 1) if log.steps else "No steps available"
    
    # Update slider max
    slider = gr.Slider(maximum=len(log.steps) if log.steps else 100, value=1)
    
    return summary, step_details, slider


def update_step_details(log_filepath, step_num):
    """Update step details when slider changes."""
    if not log_filepath:
        return "Please select a log file"
    
    log = load_log_file(log_filepath)
    if not log:
        return "Error loading log file"
    
    return format_step_details(log, int(step_num))


def list_recent_logs(log_dir: str = "logs") -> list[str]:
    """List recent log files."""
    log_path = Path(log_dir)
    if not log_path.exists():
        return []
    
    json_files = list(log_path.glob("*.json"))
    json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    return [str(f) for f in json_files[:20]]


# Create Gradio interface
with gr.Blocks(title="Game Run Visualizer") as demo:
    gr.Markdown("# 🎮 Game Run Step-by-Step Viewer")
    gr.Markdown("Select a game log to replay the agent's actions step by step")
    
    with gr.Row():
        with gr.Column(scale=1):
            log_dropdown = gr.Dropdown(
                choices=list_recent_logs(),
                label="📁 Select Log File",
                interactive=True
            )
            
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Files", size="sm")
                load_btn = gr.Button("▶️ Load Log", variant="primary", size="sm")
            
            gr.Markdown("---")
            
            summary_text = gr.Markdown("Select a log to see summary")
            
            gr.Markdown("""
            ---
            ### 💡 Navigation Tips
            - Use slider to jump to any step
            - Arrow keys: ← Previous | → Next
            """)
        
        with gr.Column(scale=2):
            with gr.Row():
                prev_btn = gr.Button("⬅️ Previous", size="sm")
                step_slider = gr.Slider(
                    minimum=1,
                    maximum=100,
                    value=1,
                    step=1,
                    label="🎬 Step Number",
                    interactive=True
                )
                next_btn = gr.Button("➡️ Next", size="sm")
            
            step_details = gr.Markdown("Select a log and step to view details", elem_classes="step-details")
    
    # Helper functions for navigation
    def go_previous(current_step):
        return max(1, current_step - 1)
    
    def go_next(current_step, max_steps):
        return min(max_steps, current_step + 1)
    
    # Event handlers
    refresh_btn.click(
        fn=lambda: gr.Dropdown(choices=list_recent_logs()),
        inputs=[],
        outputs=[log_dropdown]
    )
    
    load_btn.click(
        fn=load_and_visualize,
        inputs=[log_dropdown],
        outputs=[summary_text, step_details, step_slider]
    )
    
    step_slider.change(
        fn=update_step_details,
        inputs=[log_dropdown, step_slider],
        outputs=[step_details]
    )
    
    # Navigation buttons
    prev_btn.click(
        fn=go_previous,
        inputs=[step_slider],
        outputs=[step_slider]
    )
    
    next_btn.click(
        fn=lambda step, dropdown: go_next(step, len(load_log_file(dropdown).steps) if dropdown and load_log_file(dropdown) else 100),
        inputs=[step_slider, log_dropdown],
        outputs=[step_slider]
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, inbrowser=True)
