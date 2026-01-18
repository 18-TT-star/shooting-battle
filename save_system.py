"""Save and load game progress."""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

_SAVE_DIR = Path(__file__).resolve().parent / "saves"
_SAVE_FILE_1 = _SAVE_DIR / "save_slot_1.json"
_SAVE_FILE_2 = _SAVE_DIR / "save_slot_2.json"


def _ensure_save_directory():
    """Create save directory if it doesn't exist."""
    _SAVE_DIR.mkdir(exist_ok=True)


def save_game(slot: int, game_data: Dict[str, Any]) -> bool:
    """
    Save game data to specified slot.
    
    Args:
        slot: Save slot number (1 or 2)
        game_data: Dictionary containing game state to save
        
    Returns:
        True if save successful, False otherwise
    """
    if slot not in (1, 2):
        return False
    
    _ensure_save_directory()
    save_file = _SAVE_FILE_1 if slot == 1 else _SAVE_FILE_2
    
    try:
        with open(save_file, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Save failed: {e}")
        return False


def load_game(slot: int) -> Optional[Dict[str, Any]]:
    """
    Load game data from specified slot.
    
    Args:
        slot: Save slot number (1 or 2)
        
    Returns:
        Dictionary containing game state, or None if load failed
    """
    if slot not in (1, 2):
        return None
    
    save_file = _SAVE_FILE_1 if slot == 1 else _SAVE_FILE_2
    
    if not save_file.exists():
        return None
    
    try:
        with open(save_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Load failed: {e}")
        return None


def delete_save(slot: int) -> bool:
    """
    Delete save data from specified slot.
    
    Args:
        slot: Save slot number (1 or 2)
        
    Returns:
        True if delete successful, False otherwise
    """
    if slot not in (1, 2):
        return False
    
    save_file = _SAVE_FILE_1 if slot == 1 else _SAVE_FILE_2
    
    try:
        if save_file.exists():
            save_file.unlink()
        return True
    except Exception as e:
        print(f"Delete failed: {e}")
        return False


def get_save_info(slot: int) -> Optional[Dict[str, Any]]:
    """
    Get save file information without loading full game state.
    
    Args:
        slot: Save slot number (1 or 2)
        
    Returns:
        Dictionary with save info (levels cleared, unlocks, etc.), or None if no save
    """
    data = load_game(slot)
    if not data:
        return None
    
    return {
        'levels_cleared': sum(1 for cleared in data.get('level_cleared', []) if cleared),
        'total_levels': len(data.get('level_cleared', [])),
        'unlocked_homing': data.get('unlocked_homing', False),
        'unlocked_spread': data.get('unlocked_spread', False),
        'unlocked_dash': data.get('unlocked_dash', False),
        'unlocked_leaf_shield': data.get('unlocked_leaf_shield', False),
        'unlocked_hp_boost': data.get('unlocked_hp_boost', False),
        'level_cleared_no_equipment': data.get('level_cleared_no_equipment', [False]*7),
        'level_cleared_rainbow_star': data.get('level_cleared_rainbow_star', [False]*7),
    }


def create_save_data(level_cleared, unlocked_homing, unlocked_leaf_shield, 
                     unlocked_spread, unlocked_dash, unlocked_hp_boost, level_cleared_no_equipment, level_cleared_rainbow_star, equipment_enabled) -> Dict[str, Any]:
    """
    Create a save data dictionary from current game state.
    
    Returns:
        Dictionary ready to be saved
    """
    return {
        'level_cleared': level_cleared,
        'unlocked_homing': unlocked_homing,
        'unlocked_leaf_shield': unlocked_leaf_shield,
        'unlocked_spread': unlocked_spread,
        'unlocked_dash': unlocked_dash,
        'unlocked_hp_boost': unlocked_hp_boost,
        'level_cleared_no_equipment': level_cleared_no_equipment,
        'level_cleared_rainbow_star': level_cleared_rainbow_star,
        'equipment_enabled': equipment_enabled,
    }
