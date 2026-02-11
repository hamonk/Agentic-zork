#!/usr/bin/env python3
"""
Script to explore and document Jericho FrotzEnv methods.
"""
import os
import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from games.zork_env import TextAdventureEnv

def explore_jericho_methods():
    """Explore all available FrotzEnv methods and document what they return."""
    
    # Create environment with zork1
    wrapper = TextAdventureEnv(game="zork1")
    env = wrapper.env  # Get the underlying FrotzEnv instance
    
    print("=" * 80)
    print("JERICHO FROZENV METHODS EXPLORATION")
    print("=" * 80)
    print()
    
    # 1. reset - Initialize the game
    print("1. reset()")
    print("   Description: Resets the game to its initial state")
    obs, info = env.reset()
    print(f"   Returns: (observation: str, info: dict)")
    print(f"   Observation preview: {obs[:100]}...")
    print(f"   Info keys: {info.keys()}")
    print()
    
    # 2. get_player_location
    print("2. get_player_location()")
    print("   Description: Returns current location information")
    location = env.get_player_location()
    print(f"   Returns: {type(location).__name__}")
    print(f"   Value: {location}")
    print()
    
    # 3. get_score
    print("3. get_score()")
    print("   Description: Returns current score")
    score = env.get_score()
    print(f"   Returns: {type(score).__name__}")
    print(f"   Value: {score}")
    print()
    
    # 4. get_max_score
    print("4. get_max_score()")
    print("   Description: Returns maximum possible score")
    max_score = env.get_max_score()
    print(f"   Returns: {type(max_score).__name__}")
    print(f"   Value: {max_score}")
    print()
    
    # 5. get_moves
    print("5. get_moves()")
    print("   Description: Returns number of moves taken")
    moves = env.get_moves()
    print(f"   Returns: {type(moves).__name__}")
    print(f"   Value: {moves}")
    print()
    
    # 6. game_over
    print("6. game_over()")
    print("   Description: Checks if the game has ended")
    is_over = env.game_over()
    print(f"   Returns: {type(is_over).__name__}")
    print(f"   Value: {is_over}")
    print()
    
    # 7. get_inventory
    print("7. get_inventory()")
    print("   Description: Returns list of items in player's inventory")
    inventory = env.get_inventory()
    print(f"   Returns: {type(inventory).__name__}")
    print(f"   Value: {inventory}")
    print()
    
    # 8. get_world_objects
    print("8. get_world_objects()")
    print("   Description: Returns all objects in the game world")
    world_objects = env.get_world_objects()
    print(f"   Returns: {type(world_objects).__name__}")
    print(f"   Count: {len(world_objects)}")
    print(f"   Sample (first 3): {world_objects[:3]}")
    print()
    
    # 9. get_player_object
    print("9. get_player_object()")
    print("   Description: Returns the player object")
    player_obj = env.get_player_object()
    print(f"   Returns: {type(player_obj).__name__}")
    print(f"   Value: {player_obj}")
    print()
    
    # 10. get_object (requires object number)
    print("10. get_object(obj_num)")
    print("    Description: Returns details about a specific object by number")
    # Get object by its number (integer ID)
    obj_details = env.get_object(1)  # Get object #1
    print(f"    Returns: {type(obj_details).__name__}")
    print(f"    Example (object 1): {obj_details}")
    print()
    
    # 11. get_dictionary
    print("11. get_dictionary()")
    print("    Description: Returns the game's recognized vocabulary")
    dictionary = env.get_dictionary()
    print(f"    Returns: {type(dictionary).__name__}")
    print(f"    Count: {len(dictionary)}")
    print(f"    Sample words: {list(dictionary)[:10]}")
    print()
    
    # 12. get_valid_actions
    print("12. get_valid_actions()")
    print("    Description: Returns list of valid actions from current state")
    valid_actions = env.get_valid_actions()
    print(f"    Returns: {type(valid_actions).__name__}")
    print(f"    Count: {len(valid_actions)}")
    print(f"    Sample actions: {valid_actions[:5]}")
    print()
    
    # 13. step - Execute an action
    print("13. step(action)")
    print("    Description: Executes an action and returns new state")
    obs, reward, done, info = env.step("look")
    print(f"    Returns: (observation: str, reward: float, done: bool, info: dict)")
    print(f"    Observation preview: {obs[:80]}...")
    print(f"    Reward: {reward}")
    print(f"    Done: {done}")
    print(f"    Info keys: {info.keys()}")
    print()
    
    # 14. get_state
    print("14. get_state()")
    print("    Description: Returns serialized game state for saving")
    state = env.get_state()
    print(f"    Returns: {type(state).__name__}")
    print(f"    Size: {len(state)} bytes")
    print()
    
    # 15. set_state
    print("15. set_state(state)")
    print("    Description: Restores game to a previously saved state")
    print("    Usage: Pass state from get_state() to restore")
    env.set_state(state)
    print("    State restored successfully")
    print()
    
    # 16. get_world_state_hash
    print("16. get_world_state_hash()")
    print("    Description: Returns hash of current world state (for deduplication)")
    state_hash = env.get_world_state_hash()
    print(f"    Returns: {type(state_hash).__name__}")
    print(f"    Value: {state_hash}")
    print()
    
    # 17. get_walkthrough
    print("17. get_walkthrough()")
    print("    Description: Returns optimal solution walkthrough for the game")
    walkthrough = env.get_walkthrough()
    print(f"    Returns: {type(walkthrough).__name__}")
    print(f"    Length: {len(walkthrough)} steps")
    print(f"    First 5 steps: {walkthrough[:5]}")
    print()
    
    # 18. seed
    print("18. seed(seed_value)")
    print("    Description: Sets random seed for reproducibility")
    result = env.seed(42)
    print(f"    Returns: {type(result).__name__}")
    print(f"    Value: {result}")
    print()
    
    # 19. bindings
    print("19. bindings")
    print("    Description: Access to low-level Jericho bindings")
    bindings = env.bindings
    print(f"    Type: {type(bindings).__name__}")
    print(f"    Module: {bindings.__class__.__module__}")
    print()
    
    # 20. copy
    print("20. copy()")
    print("    Description: Creates a deep copy of the environment")
    env_copy = env.copy()
    print(f"    Returns: {type(env_copy).__name__}")
    print("    New environment instance created")
    print()
    
    # 21. load
    print("21. load(save_file)")
    print("    Description: Load game from a save file")
    print("    Usage: Pass path to .sav file to restore game state")
    print()
    
    # 22. close
    print("22. close()")
    print("    Description: Cleanup and close the environment")
    env.close()
    print("    Environment closed")
    print()
    
    print("=" * 80)
    print("EXPLORATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    explore_jericho_methods()
