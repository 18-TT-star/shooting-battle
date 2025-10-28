"""Generate a short 'beep' sound for menu navigation."""
import numpy as np
import wave

# パラメータ
SAMPLE_RATE = 44100  # Hz
DURATION = 0.08  # 秒（短い「ピッ」）
FREQUENCY = 1200  # Hz（高めのピッチ）

# サンプル数
num_samples = int(SAMPLE_RATE * DURATION)

# 時間軸
t = np.linspace(0, DURATION, num_samples, endpoint=False)

# 基本波形（サイン波）
wave_data = np.sin(2 * np.pi * FREQUENCY * t)

# エンベロープ（ADSR風）
attack_samples = int(0.005 * SAMPLE_RATE)  # 5ms
decay_samples = int(0.015 * SAMPLE_RATE)   # 15ms
release_samples = int(0.020 * SAMPLE_RATE) # 20ms

envelope = np.ones(num_samples)

# アタック（0→1）
if attack_samples > 0:
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

# リリース（1→0、最後から）
if release_samples > 0 and release_samples < num_samples:
    envelope[-release_samples:] = np.linspace(1, 0, release_samples)

# エンベロープを適用
wave_data = wave_data * envelope

# 音量調整（0.4倍）
wave_data = wave_data * 0.4

# 16bit PCMに変換
wave_data_int = np.int16(wave_data * 32767)

# WAVファイルとして保存
output_path = "assets/audio/menu_beep.wav"
with wave.open(output_path, 'w') as wav_file:
    wav_file.setnchannels(1)  # モノラル
    wav_file.setsampwidth(2)  # 16bit
    wav_file.setframerate(SAMPLE_RATE)
    wav_file.writeframes(wave_data_int.tobytes())

print(f"Menu beep sound saved to {output_path}")
