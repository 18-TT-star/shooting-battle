#!/usr/bin/env python3
"""Generate a Mario Star power-up transformation sound effect (Starman invincibility theme)."""

import numpy as np
import wave
import struct

# Parameters
sample_rate = 44100
duration = 0.8  # seconds

# Generate time array
t = np.linspace(0, duration, int(sample_rate * duration))

# Mario Star power-up: rapid ascending arpeggios (ギュインギュインギュイン)
# Based on the iconic invincibility theme - fast repeating upward notes
# Pattern: C-D-E-C-D-E-C-D-E (3 repetitions of the arpeggio)
note_sequence = [
    # First "ギュイン" - C5, E5, G5
    (523.25, 0.00, 0.08),   # C5
    (659.25, 0.08, 0.16),   # E5
    (783.99, 0.16, 0.24),   # G5
    
    # Second "ギュイン" - slightly higher
    (587.33, 0.24, 0.32),   # D5
    (739.99, 0.32, 0.40),   # F#5
    (880.00, 0.40, 0.48),   # A5
    
    # Third "ギュイン" - even higher
    (659.25, 0.48, 0.56),   # E5
    (830.61, 0.56, 0.64),   # G#5
    (987.77, 0.64, 0.75),   # B5
]

signal = np.zeros_like(t)

for freq, start_time, end_time in note_sequence:
    # Create note window
    note_mask = (t >= start_time) & (t < end_time)
    note_t = t[note_mask] - start_time
    note_duration = end_time - start_time
    
    # Square-ish wave for that classic 8-bit sound (more harmonics)
    note_signal = np.zeros_like(note_t)
    
    # Add multiple harmonics for rich, bright sound
    for harmonic in range(1, 8):
        amplitude = 0.6 / harmonic  # Decreasing amplitude for higher harmonics
        note_signal += amplitude * np.sin(2 * np.pi * freq * harmonic * note_t)
    
    # Fast attack, short sustain for "ギュイン" effect
    envelope = np.ones_like(note_t)
    attack_time = 0.005  # Very fast attack
    release_time = 0.03   # Quick release
    
    # Attack
    attack_samples = int(attack_time * sample_rate)
    if len(note_t) > attack_samples:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    
    # Release
    release_samples = int(release_time * sample_rate)
    if len(note_t) > release_samples:
        envelope[-release_samples:] = np.linspace(1, 0, release_samples)
    
    signal[note_mask] = note_signal * envelope

# Add slight modulation for more energetic feel
modulation_freq = 30  # Hz - fast modulation
modulation_depth = 0.15
signal = signal * (1 + modulation_depth * np.sin(2 * np.pi * modulation_freq * t))

# Overall fade out at the end
fade_out_duration = 0.1
fade_out_samples = int(fade_out_duration * sample_rate)
signal[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)

# Normalize to prevent clipping
max_val = np.max(np.abs(signal))
if max_val > 0:
    signal = signal / max_val * 0.85  # Leave headroom

# Convert to 16-bit PCM
signal_int = (signal * 32767).astype(np.int16)

# Save as WAV file
output_path = "assets/audio/transform.wav"
with wave.open(output_path, 'w') as wav_file:
    wav_file.setnchannels(1)  # Mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(sample_rate)
    wav_file.writeframes(signal_int.tobytes())

print(f"✅ Created Mario Star power-up sound: {output_path}")
print(f"   Duration: {duration}s, Sample rate: {sample_rate}Hz")
print(f"   Style: 'ギュインギュインギュイン' - Rapid ascending arpeggios")
print(f"   Pattern: 3 sets of rising triads (C-E-G, D-F#-A, E-G#-B)")

