#!/usr/bin/env python3
"""Generate a Mario Star power-up transformation sound effect (Starman invincibility theme)."""

import wave
import struct
import math

# Parameters
sample_rate = 44100
duration = 0.8  # seconds

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

num_samples = int(sample_rate * duration)

# Save as WAV file
output_path = "assets/audio/transform.wav"
with wave.open(output_path, 'w') as wav_file:
    wav_file.setnchannels(1)  # Mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(sample_rate)
    
    for i in range(num_samples):
        t = i / sample_rate
        signal = 0.0
        
        # Generate signal for each note
        for freq, start_time, end_time in note_sequence:
            if start_time <= t < end_time:
                note_t = t - start_time
                note_duration = end_time - start_time
                
                # Add multiple harmonics for rich, bright sound
                note_signal = 0.0
                for harmonic in range(1, 8):
                    amplitude = 0.6 / harmonic
                    note_signal += amplitude * math.sin(2 * math.pi * freq * harmonic * note_t)
                
                # Fast attack, short sustain for "ギュイン" effect
                envelope = 1.0
                attack_time = 0.005  # Very fast attack
                release_time = 0.03   # Quick release
                
                # Attack
                if note_t < attack_time:
                    envelope = note_t / attack_time
                
                # Release
                time_until_end = end_time - t
                if time_until_end < release_time:
                    envelope = time_until_end / release_time
                
                signal += note_signal * envelope
        
        # Add slight modulation for more energetic feel
        modulation_freq = 30  # Hz - fast modulation
        modulation_depth = 0.15
        signal *= (1 + modulation_depth * math.sin(2 * math.pi * modulation_freq * t))
        
        # Overall fade out at the end
        fade_out_duration = 0.1
        if t > duration - fade_out_duration:
            fade_ratio = (duration - t) / fade_out_duration
            signal *= fade_ratio
        
        # Normalize and convert to 16-bit PCM
        signal = max(-0.85, min(0.85, signal))  # Clamp to prevent distortion
        sample = int(signal * 32767)
        wav_file.writeframes(struct.pack('<h', sample))

print(f"✅ Created Mario Star power-up sound: {output_path}")
print(f"   Duration: {duration}s, Sample rate: {sample_rate}Hz")
print(f"   Style: 'ギュインギュインギュイン' - Rapid ascending arpeggios")
print(f"   Pattern: 3 sets of rising triads (C-E-G, D-F#-A, E-G#-B)")


