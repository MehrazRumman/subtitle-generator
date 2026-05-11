#!/usr/bin/env python3
"""
Subtitle generator: transcribes a video file and writes a .srt subtitle file.
Uses faster-whisper for accurate transcription with proper timestamps.

Usage:
  python subtitle_generator.py movie.mp4
  python subtitle_generator.py movie.mp4 --model small --translate
"""

import sys
import argparse
import subprocess
import tempfile
import os
from pathlib import Path

from faster_whisper import WhisperModel
from tqdm import tqdm


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    ms = round(seconds * 1000)
    h  = ms // 3_600_000;  ms %= 3_600_000
    m  = ms // 60_000;     ms %= 60_000
    s  = ms // 1_000;      ms %= 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def get_duration(path: str) -> float:
    """Return duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def extract_audio(video_path: Path, out_wav: str, duration: float) -> None:
    """Extract mono 16 kHz WAV audio from a video file, showing a tqdm progress bar."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-ar", "16000", "-ac", "1", "-f", "wav",
        "-progress", "pipe:1", "-nostats",
        out_wav,
        "-loglevel", "error",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    bar = tqdm(total=100, desc="Extracting audio", unit="%",
               bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}%  [{elapsed}<{remaining}]")
    last_pct = 0

    for line in proc.stdout:
        line = line.strip()
        # ffmpeg -progress emits `out_time_us=<microseconds>`
        if line.startswith("out_time_us="):
            try:
                us = int(line.split("=")[1])
                if duration > 0:
                    pct = min(int(us / (duration * 1_000_000) * 100), 100)
                    bar.update(pct - last_pct)
                    last_pct = pct
            except ValueError:
                pass

    proc.wait()
    bar.update(100 - last_pct)
    bar.close()

    if proc.returncode != 0:
        err = proc.stderr.read()
        print(f"\nffmpeg error:\n{err}", file=sys.stderr)
        print("Make sure ffmpeg is installed: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)


def transcribe_to_srt(
    audio_path: str,
    duration: float,
    model: WhisperModel,
    language: str | None,
    translate: bool,
) -> str:
    """Transcribe audio with a tqdm progress bar and return SRT content."""
    task = "translate" if translate else "transcribe"

    segments, info = model.transcribe(
        audio_path,
        task=task,
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    detected = getattr(info, "language", "unknown")
    print(f"  Detected language : {detected.upper()}")
    print(f"  Task              : {'translate → English' if translate else f'transcribe ({detected.upper()})'}")

    bar = tqdm(total=100, desc="Transcribing   ", unit="%",
               bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}%  [{elapsed}<{remaining}]")
    last_pct = 0

    blocks = []
    idx = 1
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        start = format_timestamp(seg.start)
        end   = format_timestamp(seg.end)
        blocks.append(f"{idx}\n{start} --> {end}\n{text}")
        idx += 1

        if duration > 0:
            pct = min(int(seg.end / duration * 100), 100)
            bar.update(pct - last_pct)
            last_pct = pct

    bar.update(100 - last_pct)
    bar.close()

    return "\n\n".join(blocks) + "\n"


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def main():
    ap = argparse.ArgumentParser(
        description="Generate a .srt subtitle file from a video file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python subtitle_generator.py movie.mp4
  python subtitle_generator.py movie.mp4 --model small
  python subtitle_generator.py movie.mp4 --translate
  python subtitle_generator.py movie.mp4 --language ta --translate
  python subtitle_generator.py movie.mp4 --output /tmp/custom.srt

Model sizes (accuracy vs speed):
  tiny   ~39 MB   fastest
  base   ~74 MB   good balance [default]
  small  ~244 MB  better accuracy
  medium ~769 MB  great accuracy
  large  ~1550 MB best accuracy

Loading the .srt in VLC:
  VLC auto-loads the .srt if it is in the same folder as the video
  and has the same base name (e.g. movie.mp4 → movie.srt).
  Or: Subtitles → Add Subtitle File… to load it manually.
""",
    )
    ap.add_argument("video", help="Path to the input video file")
    ap.add_argument(
        "--model", default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)",
    )
    ap.add_argument(
        "--language", default=None,
        help="Source language code, e.g. 'ja', 'ta', 'es' (default: auto-detect)",
    )
    ap.add_argument(
        "--translate", action="store_true",
        help="Translate subtitles to English (regardless of source language)",
    )
    ap.add_argument(
        "--output", "-o", default=None,
        help="Output .srt file path (default: same folder and name as video)",
    )
    args = ap.parse_args()

    # ── Validate input ────────────────────────────────────────────────────────
    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        print(f"Error: video file not found: {video}", file=sys.stderr)
        sys.exit(1)

    if not check_ffmpeg():
        print("Error: ffmpeg is not installed.", file=sys.stderr)
        print("Install it with:  brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    srt_path = Path(args.output).expanduser().resolve() if args.output else video.with_suffix(".srt")

    print(f"\n{'─'*55}")
    print(f"  Video  : {video.name}")
    print(f"  Model  : {args.model}")
    print(f"  Output : {srt_path.name}")
    print(f"{'─'*55}\n")

    # ── Get video duration for progress bars ──────────────────────────────────
    duration = get_duration(str(video))

    # ── Load model ────────────────────────────────────────────────────────────
    print("Loading Whisper model… (first run downloads model weights)")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    print("Model ready.\n")

    # ── Extract audio to temp file ────────────────────────────────────────────
    tmp_fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
    os.close(tmp_fd)

    try:
        extract_audio(video, tmp_wav, duration)
        print()

        # ── Transcribe ────────────────────────────────────────────────────────
        srt_content = transcribe_to_srt(tmp_wav, duration, model, args.language, args.translate)
    finally:
        os.unlink(tmp_wav)

    # ── Write .srt ────────────────────────────────────────────────────────────
    srt_path.write_text(srt_content, encoding="utf-8")

    print(f"\n{'─'*55}")
    print(f"  Done! Subtitle file saved:")
    print(f"  {srt_path}")
    print(f"{'─'*55}")
    print("\nTo play with subtitles:")
    print(f"  vlc \"{video}\"")
    print("  (VLC auto-loads the .srt if it has the same name as the video)\n")


if __name__ == "__main__":
    main()
