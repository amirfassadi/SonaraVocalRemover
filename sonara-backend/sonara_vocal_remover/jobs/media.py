import subprocess
import wave
from pathlib import Path


def normalize(source, destination, max_seconds):
    """Bound decoded output, not only compressed bytes; rejects corrupt/truncated media."""
    destination = Path(destination)
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-y',
                    '-protocol_whitelist', 'file,pipe', '-format_whitelist', 'wav,mp3,flac,mov,ogg', '-i', str(source),
                    '-map', '0:a:0', '-vn', '-t', str(max_seconds + 1),
                    '-ac', '2', '-ar', '44100', '-c:a', 'pcm_s16le', str(destination)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
    with wave.open(str(destination)) as audio:
        duration = audio.getnframes() / audio.getframerate()
        if not 0 < duration <= max_seconds:
            raise ValueError('invalid_duration')
    return duration


def validate_outputs(directory, source_duration):
    lengths = []
    for name in ('vocals', 'instrumental'):
        source = directory / f'{name}.wav'
        final = directory / f'{name}.pcm.wav'
        duration = normalize(source, final, source_duration + 0.1)
        if abs(duration - source_duration) > 0.1:
            raise ValueError('invalid_output_duration')
        lengths.append(duration)
        final.replace(source)
    if abs(lengths[0] - lengths[1]) > 1 / 44100:
        raise ValueError('unaligned_stems')
