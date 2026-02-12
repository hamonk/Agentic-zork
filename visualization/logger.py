"""Structured logging for game runs."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class StepLog:
    """Log entry for a single agent step."""
    step: int
    thought: str
    tool: str
    tool_args: dict[str, Any]
    result: str
    location: str
    score: int
    moves: int
    inventory: list[str] = field(default_factory=list)
    valid_actions: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    

@dataclass
class GameRunLog:
    """Complete log for a game run."""
    game: str
    agent: str
    start_time: str
    end_time: Optional[str] = None
    seed: int = 42
    max_steps: int = 100
    final_score: int = 0
    final_moves: int = 0
    locations_visited: list[str] = field(default_factory=list)
    game_completed: bool = False
    error: Optional[str] = None
    steps: list[StepLog] = field(default_factory=list)
    map_state: dict[str, list[str]] = field(default_factory=dict)
    
    def add_step(self, step_log: StepLog):
        """Add a step to the log."""
        self.steps.append(step_log)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def save(self, filepath: str | Path):
        """Save log to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str | Path) -> 'GameRunLog':
        """Load log from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Convert step dicts back to StepLog objects
        if 'steps' in data:
            data['steps'] = [StepLog(**step) for step in data['steps']]
        
        return cls(**data)


class GameLogger:
    """Manager for game run logging."""
    
    def __init__(self, log_dir: str | Path = "logs"):
        """Initialize logger with output directory."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_log: Optional[GameRunLog] = None
        self.current_filepath: Optional[Path] = None
    
    def start_run(self, game: str, agent: str, seed: int, max_steps: int) -> GameRunLog:
        """Start a new game run log."""
        self.current_log = GameRunLog(
            game=game,
            agent=agent,
            start_time=datetime.now().isoformat(),
            seed=seed,
            max_steps=max_steps
        )
        
        # Generate filename immediately
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{game}_{agent}_{timestamp}.json"
        self.current_filepath = self.log_dir / filename
        
        # Save initial empty log
        self.current_log.save(self.current_filepath)
        
        return self.current_log
    
    def log_step(
        self,
        step: int,
        thought: str,
        tool: str,
        tool_args: dict,
        result: str,
        location: str,
        score: int,
        moves: int,
        inventory: list[str] = None,
        valid_actions: list[str] = None
    ):
        """Log a single step."""
        if not self.current_log:
            raise RuntimeError("No active log. Call start_run() first.")
        
        step_log = StepLog(
            step=step,
            thought=thought,
            tool=tool,
            tool_args=tool_args,
            result=result,
            location=location,
            score=score,
            moves=moves,
            inventory=inventory or [],
            valid_actions=valid_actions or []
        )
        
        self.current_log.add_step(step_log)
        
        # Save incrementally after each step
        if self.current_filepath:
            self.current_log.save(self.current_filepath)
    
    def end_run(
        self,
        final_score: int,
        final_moves: int,
        locations_visited: list[str],
        game_completed: bool,
        map_state: dict[str, list[str]] = None,
        error: Optional[str] = None
    ) -> str:
        """End the current run and save to file."""
        if not self.current_log:
            raise RuntimeError("No active log. Call start_run() first.")
        
        self.current_log.end_time = datetime.now().isoformat()
        self.current_log.final_score = final_score
        self.current_log.final_moves = final_moves
        self.current_log.locations_visited = locations_visited
        self.current_log.game_completed = game_completed
        self.current_log.map_state = map_state or {}
        self.current_log.error = error
        
        # Use existing filepath (already set in start_run)
        filepath = self.current_filepath or self.log_dir / f"{self.current_log.game}_final.json"
        
        # Save final state
        self.current_log.save(filepath)
        
        return str(filepath)
