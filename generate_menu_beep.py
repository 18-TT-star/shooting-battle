"""Generate a short 'beep' sound for menu navigation."""
import wave
import math
import struct

# パラメータ
SAMPLE_RATE = 44100  # Hz
DURATION = 0.08  # 秒（短い「ピッ」）
FREQUENCY = 1200  # Hz（高めのピッチ）

num_samples = int(SAMPLE_RATE * DURATION)

# WAVファイルとして保存
output_path = "assets/audio/menu_beep.wav"
with wave.open(output_path, 'w') as wav_file:
    wav_file.setnchannels(1)  # モノラル
    wav_file.setsampwidth(2)  # 16bit
    wav_file.setframerate(SAMPLE_RATE)
    
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # サイン波
        value = math.sin(2 * math.pi * FREQUENCY * t)
        # エンベロープ（簡易的にフェードアウト）
        envelope = 1.0 - (t / DURATION) * 0.7
        value *= envelope * 0.4
        # 16bit PCM
        sample = int(value * 32767)
        wav_file.writeframes(struct.pack('<h', sample))

print(f"Menu beep sound saved to {output_path}")

