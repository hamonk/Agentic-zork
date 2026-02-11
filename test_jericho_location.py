#!/usr/bin/env python
"""Test script to explore Jericho's location tracking capabilities."""

from jericho import FrotzEnv
from pathlib import Path

# Load zork1
game_path = Path('z-machine-games-master/jericho-game-suite/zork1.z5')
env = FrotzEnv(str(game_path))
obs, info = env.reset()

print('=== Initial State ===')
print('Observation:', obs[:100], '...')
print()

# Check what get_player_location returns
try:
    loc = env.get_player_location()
    print('get_player_location():', loc)
    print('Type:', type(loc))
    print('Attributes:', [x for x in dir(loc) if not x.startswith('_')])
    
    # Try to access attributes
    if hasattr(loc, 'num'):
        print('  loc.num:', loc.num)
    if hasattr(loc, 'name'):
        print('  loc.name:', loc.name)
    if hasattr(loc, 'parent'):
        print('  loc.parent:', loc.parent)
    print()
except Exception as e:
    print('Error calling get_player_location():', e)
    print()

# Check what get_player_object returns
try:
    player_obj = env.get_player_object()
    print('get_player_object():', player_obj)
    print('Type:', type(player_obj))
    if hasattr(player_obj, 'num'):
        print('  player_obj.num:', player_obj.num)
    if hasattr(player_obj, 'name'):
        print('  player_obj.name:', player_obj.name)
    if hasattr(player_obj, 'parent'):
        print('  player_obj.parent:', player_obj.parent)
    print()
except Exception as e:
    print('Error calling get_player_object():', e)
    print()

# Check get_world_objects
try:
    world_objs = env.get_world_objects()
    print('get_world_objects() count:', len(world_objs))
    if world_objs:
        print('First 3 objects:')
        for i, obj in enumerate(world_objs[:3]):
            attrs = []
            if hasattr(obj, 'num'):
                attrs.append(f'num={obj.num}')
            if hasattr(obj, 'name'):
                attrs.append(f'name={obj.name}')
            if hasattr(obj, 'parent'):
                attrs.append(f'parent={obj.parent}')
            print(f'  {i}: {obj} ({", ".join(attrs)})')
    print()
except Exception as e:
    print('Error calling get_world_objects():', e)
    print()

# Check get_world_state_hash
try:
    hash1 = env.get_world_state_hash()
    print('get_world_state_hash():', hash1)
    print('Type:', type(hash1))
    print()
except Exception as e:
    print('Error calling get_world_state_hash():', e)
    print()

# Test movement and track location changes
print('=== Testing Movement ===')
actions = ['north', 'south', 'east', 'west', 'open mailbox']

for action in actions:
    obs, reward, done, info = env.step(action)
    print(f'\nAction: {action}')
    print(f'  Observation: {obs[:80]}...')
    print(f'  Score: {info.get("score", 0)}, Moves: {info.get("moves", 0)}')
    
    try:
        loc = env.get_player_location()
        loc_info = f'{loc}'
        if hasattr(loc, 'num'):
            loc_info += f' (num={loc.num})'
        if hasattr(loc, 'name'):
            loc_info += f' (name={loc.name})'
        print(f'  Location object: {loc_info}')
    except Exception as e:
        print(f'  Error getting location: {e}')

print('\n=== Summary ===')
print('Jericho provides get_player_location() which returns a location object.')
print('This object likely has attributes like:')
print('  - num: numeric ID for the room')
print('  - name: string name of the location')
print('  - parent: parent container (if applicable)')
