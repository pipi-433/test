from __future__ import annotations

import argparse
import audioop
import math
import shutil
import struct
import wave
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLIP_DIR = PROJECT_ROOT / "external" / "avatar-clips"
DEFAULT_BACKUP_DIR = DEFAULT_CLIP_DIR / "_source_backup"


@dataclass(frozen=True)
class AudioStats:
    channels: int
    sample_width: int
    sample_rate: int
    frames: int
    duration_seconds: float
    peak: int
    rms: float
    rms_dbfs: float | None
    long_silence_count: int


def _read_wav(path: Path) -> tuple[bytes, int, int, int]:
    with wave.open(str(path), "rb") as reader:
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()
        sample_rate = reader.getframerate()
        frames = reader.getnframes()
        raw = reader.readframes(frames)
    return raw, channels, sample_width, sample_rate


def _write_wav(path: Path, pcm16: bytes, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(pcm16)


def _to_mono_pcm16(raw: bytes, channels: int, sample_width: int) -> bytes:
    pcm = raw
    if sample_width != 2:
        pcm = audioop.lin2lin(pcm, sample_width, 2)
    if channels == 2:
        pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
    elif channels > 2:
        samples = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
        mixed: list[int] = []
        for index in range(0, len(samples), channels):
            mixed.append(round(sum(samples[index : index + channels]) / channels))
        pcm = struct.pack("<" + "h" * len(mixed), *mixed)
    return pcm


def _resample_pcm16(pcm16: bytes, source_rate: int, target_rate: int) -> bytes:
    if source_rate == target_rate:
        return pcm16
    converted, _state = audioop.ratecv(pcm16, 2, 1, source_rate, target_rate, None)
    return converted


def _samples_from_pcm16(pcm16: bytes) -> list[int]:
    if not pcm16:
        return []
    return list(struct.unpack("<" + "h" * (len(pcm16) // 2), pcm16))


def _pcm16_from_samples(samples: list[int]) -> bytes:
    if not samples:
        return b""
    clipped = [max(-32768, min(32767, int(value))) for value in samples]
    return struct.pack("<" + "h" * len(clipped), *clipped)


def _rms(samples: list[int]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(value * value for value in samples) / len(samples))


def _stats(path: Path) -> AudioStats:
    raw, channels, sample_width, sample_rate = _read_wav(path)
    frames = len(raw) // max(1, sample_width * channels)
    pcm16 = _to_mono_pcm16(raw, channels, sample_width)
    samples = _samples_from_pcm16(_resample_pcm16(pcm16, sample_rate, sample_rate))
    peak = max((abs(value) for value in samples), default=0)
    rms = _rms(samples)
    rms_dbfs = 20 * math.log10(rms / 32768) if rms > 0 else None
    long_silence_count = len(_find_long_silences(samples, sample_rate))
    return AudioStats(
        channels=channels,
        sample_width=sample_width,
        sample_rate=sample_rate,
        frames=frames,
        duration_seconds=frames / sample_rate if sample_rate else 0.0,
        peak=peak,
        rms=rms,
        rms_dbfs=rms_dbfs,
        long_silence_count=long_silence_count,
    )


def _find_long_silences(
    samples: list[int],
    sample_rate: int,
    *,
    threshold: int = 120,
    min_silence_ms: int = 260,
) -> list[tuple[int, int]]:
    if not samples:
        return []
    window = max(1, int(sample_rate * 0.02))
    min_windows = max(1, int((min_silence_ms / 1000) * sample_rate / window))
    silences: list[tuple[int, int]] = []
    run_start: int | None = None
    run_windows = 0
    for start in range(0, len(samples), window):
        chunk = samples[start : start + window]
        silent = _rms(chunk) < threshold
        if silent:
            if run_start is None:
                run_start = start
            run_windows += 1
        else:
            if run_start is not None and run_windows >= min_windows:
                silences.append((run_start, start))
            run_start = None
            run_windows = 0
    if run_start is not None and run_windows >= min_windows:
        silences.append((run_start, len(samples)))
    return silences


def _compress_silence(
    samples: list[int],
    sample_rate: int,
    *,
    threshold: int,
    max_silence_ms: int,
) -> list[int]:
    silences = _find_long_silences(samples, sample_rate, threshold=threshold, min_silence_ms=max_silence_ms + 80)
    if not silences:
        return samples
    max_silence_samples = int(sample_rate * max_silence_ms / 1000)
    output: list[int] = []
    cursor = 0
    for start, end in silences:
        output.extend(samples[cursor:start])
        keep = min(max_silence_samples, end - start)
        output.extend([0] * keep)
        cursor = end
    output.extend(samples[cursor:])
    return output


def _trim_edges(samples: list[int], *, threshold: int) -> list[int]:
    if not samples:
        return samples
    start = 0
    end = len(samples)
    while start < end and abs(samples[start]) < threshold:
        start += 1
    while end > start and abs(samples[end - 1]) < threshold:
        end -= 1
    return samples[start:end]


def _normalize_peak(samples: list[int], *, target_peak: int) -> list[int]:
    peak = max((abs(value) for value in samples), default=0)
    if peak == 0 or peak >= target_peak:
        return samples
    gain = target_peak / peak
    return [round(value * gain) for value in samples]


def normalize_wav(
    source: Path,
    target: Path,
    *,
    target_rate: int,
    silence_threshold: int,
    max_silence_ms: int,
    edge_silence_ms: int,
    target_peak: int,
) -> None:
    raw, channels, sample_width, sample_rate = _read_wav(source)
    pcm16 = _to_mono_pcm16(raw, channels, sample_width)
    pcm16 = _resample_pcm16(pcm16, sample_rate, target_rate)
    samples = _samples_from_pcm16(pcm16)
    samples = _trim_edges(samples, threshold=silence_threshold)
    samples = _compress_silence(
        samples,
        target_rate,
        threshold=silence_threshold,
        max_silence_ms=max_silence_ms,
    )
    samples = _normalize_peak(samples, target_peak=target_peak)
    edge = [0] * int(target_rate * edge_silence_ms / 1000)
    samples = edge + samples + edge
    _write_wav(target, _pcm16_from_samples(samples), target_rate)


def _candidate_wavs(clip_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in clip_dir.glob("*.wav")
        if path.is_file() and not path.name.endswith(".source.wav")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and normalize Lingjing avatar preset wav clips.")
    parser.add_argument("--clip-dir", type=Path, default=DEFAULT_CLIP_DIR)
    parser.add_argument("--target-rate", type=int, default=24000)
    parser.add_argument("--silence-threshold", type=int, default=120)
    parser.add_argument("--max-silence-ms", type=int, default=180)
    parser.add_argument("--edge-silence-ms", type=int, default=160)
    parser.add_argument("--target-peak", type=int, default=26000)
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()

    clip_dir = args.clip_dir
    if not clip_dir.is_absolute():
        clip_dir = PROJECT_ROOT / clip_dir
    clip_dir = clip_dir.resolve()
    allowed_root = DEFAULT_CLIP_DIR.resolve()
    if clip_dir != allowed_root and not clip_dir.is_relative_to(allowed_root):
        raise SystemExit(f"clip dir must stay inside {allowed_root}")

    wavs = _candidate_wavs(clip_dir)
    if not wavs:
        print(f"No wav clips found in {clip_dir}")
        return 0

    for wav_path in wavs:
        before = _stats(wav_path)
        print(
            f"{wav_path.name}: before "
            f"{before.channels}ch {before.sample_width * 8}bit {before.sample_rate}Hz "
            f"{before.duration_seconds:.3f}s peak={before.peak} rms={before.rms:.1f} "
            f"long_silences={before.long_silence_count}"
        )
        if args.report_only:
            continue
        target_path = wav_path if args.in_place else wav_path.with_name(f"{wav_path.stem}.normalized.wav")
        if args.in_place:
            DEFAULT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            backup_path = DEFAULT_BACKUP_DIR / f"{wav_path.stem}.source.wav"
            if not backup_path.exists():
                shutil.copy2(wav_path, backup_path)
                print(f"  backup: {backup_path}")
        normalize_wav(
            wav_path,
            target_path,
            target_rate=args.target_rate,
            silence_threshold=args.silence_threshold,
            max_silence_ms=args.max_silence_ms,
            edge_silence_ms=args.edge_silence_ms,
            target_peak=args.target_peak,
        )
        after = _stats(target_path)
        print(
            f"  after {target_path.name}: "
            f"{after.channels}ch {after.sample_width * 8}bit {after.sample_rate}Hz "
            f"{after.duration_seconds:.3f}s peak={after.peak} rms={after.rms:.1f} "
            f"long_silences={after.long_silence_count}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
