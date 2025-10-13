"""Lightweight audio helper for background music and sound effects."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import pygame

_AUDIO_CACHE: Dict[str, pygame.mixer.Sound] = {}
_AUDIO_DISABLED = False
_AUDIO_READY = False

_BASE_DIR = Path(__file__).resolve().parent
_AUDIO_DIR = _BASE_DIR / "assets" / "audio"


def init_audio() -> None:
    """Initialize the mixer and preload sound effects if possible."""
    global _AUDIO_DISABLED, _AUDIO_READY
    if _AUDIO_DISABLED or _AUDIO_READY:
        return
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except pygame.error:
        # Audio device unavailable; keep the game running silently.
        _AUDIO_DISABLED = True
        return
    _load_default_sounds()
    _AUDIO_READY = True


def _load_default_sounds() -> None:
    """Populate the sound cache with built-in effects."""
    _load_sound("enemy_hit", "hit_enemy.wav", volume=0.6)
    _load_sound("reflect", "reflect_hit.wav", volume=0.55)


def _load_sound(key: str, filename: str, *, volume: float = 1.0) -> None:
    if _AUDIO_DISABLED:
        return
    sound_path = _AUDIO_DIR / filename
    if not sound_path.exists():
        return
    try:
        sound = pygame.mixer.Sound(str(sound_path))
    except pygame.error:
        return
    sound.set_volume(max(0.0, min(1.0, volume)))
    _AUDIO_CACHE[key] = sound


def play_enemy_hit() -> None:
    """Play the default enemy hit effect."""
    if _AUDIO_DISABLED:
        return
    if not _AUDIO_READY:
        init_audio()
    sound = _AUDIO_CACHE.get("enemy_hit")
    if sound:
        sound.play()


def play_reflect() -> None:
    """Play the bullet reflection effect."""
    if _AUDIO_DISABLED:
        return
    if not _AUDIO_READY:
        init_audio()
    sound = _AUDIO_CACHE.get("reflect")
    if sound:
        sound.play()


def shutdown_audio() -> None:
    """Stop all sounds and free mixer resources when quitting the game."""
    global _AUDIO_READY
    if _AUDIO_DISABLED or not pygame.mixer.get_init():
        return
    pygame.mixer.stop()
    pygame.mixer.quit()
    _AUDIO_CACHE.clear()
    _AUDIO_READY = False
