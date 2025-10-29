"""Lightweight audio helper for background music and sound effects."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import pygame

_AUDIO_CACHE: Dict[str, pygame.mixer.Sound] = {}
_AUDIO_DISABLED = False
_AUDIO_READY = False
_CURRENT_TRACK: Optional[pygame.mixer.Channel] = None
_BGM_PLAYING = False  # BGMループ再生中かどうか
_CURRENT_BGM = None  # 現在再生中のBGM名

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
    _load_sound("boss_clear", "Boom5.wav", volume=0.65)
    # ボス6形態変化用の効果音（マリオ風パワーアップ音）
    _load_sound("shape_transform", "transform.wav", volume=0.7)
    # BGM用（ギュインギュインギュインをループ）
    _load_sound("bgm_main", "transform.wav", volume=0.5)
    # メニュー移動音（ピッ）
    _load_sound("menu_beep", "menu_beep.wav", volume=0.5)


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


def play_boss_clear_music() -> None:
    """Play the boss clear celebratory track."""
    global _CURRENT_TRACK
    if _AUDIO_DISABLED:
        return
    if not _AUDIO_READY:
        init_audio()
    sound = _AUDIO_CACHE.get("boss_clear")
    if not sound:
        return
    if _CURRENT_TRACK:
        _CURRENT_TRACK.stop()
    _CURRENT_TRACK = sound.play()


def stop_music() -> None:
    """Stop any long-form music currently playing."""
    global _CURRENT_TRACK, _BGM_PLAYING, _CURRENT_BGM
    if _CURRENT_TRACK:
        _CURRENT_TRACK.stop()
        _CURRENT_TRACK = None
    _BGM_PLAYING = False
    _CURRENT_BGM = None
    # pygame.mixerのミュージックチャンネルも停止
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()


def fade_out_bgm(fade_time_ms: int = 2000) -> None:
    """Fade out the current BGM over the specified time in milliseconds."""
    global _BGM_PLAYING, _CURRENT_BGM
    if _AUDIO_DISABLED:
        return
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.fadeout(fade_time_ms)
        _BGM_PLAYING = False
        _CURRENT_BGM = None


def play_bgm(bgm_name: str = "picopiconostalgie", volume: float = 0.4, fade_in_ms: int = 0) -> None:
    """Play the specified BGM in loop.
    
    Args:
        bgm_name: Name of the BGM file (without extension)
        volume: Volume level (0.0 to 1.0)
        fade_in_ms: Fade-in duration in milliseconds (0 = no fade)
    """
    global _BGM_PLAYING, _CURRENT_BGM
    if _AUDIO_DISABLED:
        return
    if not _AUDIO_READY:
        init_audio()
    
    # すでに同じBGMが再生中なら何もしない
    if _BGM_PLAYING and _CURRENT_BGM == bgm_name:
        return
    
    # BGMファイルのパスを決定
    bgm_path = _AUDIO_DIR / f"{bgm_name}.mp3"
    if not bgm_path.exists():
        # .mp3がなければ.wavを試す
        bgm_path = _AUDIO_DIR / f"{bgm_name}.wav"
        if not bgm_path.exists():
            return
    
    try:
        pygame.mixer.music.load(str(bgm_path))
        pygame.mixer.music.set_volume(volume)
        if fade_in_ms > 0:
            pygame.mixer.music.play(-1, fade_ms=fade_in_ms)  # -1 = infinite loop with fade-in
        else:
            pygame.mixer.music.play(-1)  # -1 = infinite loop
        _BGM_PLAYING = True
        _CURRENT_BGM = bgm_name
    except pygame.error:
        pass


def play_reflect() -> None:
    """Play the bullet reflection effect."""
    if _AUDIO_DISABLED:
        return
    if not _AUDIO_READY:
        init_audio()
    sound = _AUDIO_CACHE.get("reflect")
    if sound:
        sound.play()


def play_shape_transform() -> None:
    """Play the shape transformation sound effect (Mario star style)."""
    if _AUDIO_DISABLED:
        return
    if not _AUDIO_READY:
        init_audio()
    sound = _AUDIO_CACHE.get("shape_transform")
    if sound:
        sound.play()


def play_menu_beep() -> None:
    """Play the menu navigation beep sound."""
    if _AUDIO_DISABLED:
        return
    if not _AUDIO_READY:
        init_audio()
    sound = _AUDIO_CACHE.get("menu_beep")
    if sound:
        sound.play()


def fade_out_bgm(fade_time_ms: int = 1000) -> None:
    """Fade out the currently playing BGM over the specified time."""
    global _BGM_PLAYING, _CURRENT_BGM
    if _AUDIO_DISABLED or not _BGM_PLAYING:
        return
    pygame.mixer.music.fadeout(fade_time_ms)
    _BGM_PLAYING = False
    _CURRENT_BGM = None


def get_current_bgm() -> Optional[str]:
    """現在再生中のBGM名を返す"""
    return _CURRENT_BGM


def shutdown_audio() -> None:
    """Stop all sounds and free mixer resources when quitting the game."""
    global _AUDIO_READY, _CURRENT_TRACK, _BGM_PLAYING, _CURRENT_BGM
    if _AUDIO_DISABLED or not pygame.mixer.get_init():
        return
    stop_music()
    pygame.mixer.stop()
    pygame.mixer.quit()
    _AUDIO_CACHE.clear()
    _AUDIO_READY = False
    _CURRENT_TRACK = None
    _BGM_PLAYING = False
    _CURRENT_BGM = None
