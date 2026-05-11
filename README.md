# Subtitle Generator

Generate `.srt` subtitle files from any video using [faster-whisper](https://github.com/SYSTRAN/faster-whisper). Supports 90+ languages with optional English translation.

## How it works

1. Point it at a video file
2. It extracts the audio and transcribes it with Whisper
3. A `.srt` file is saved next to your video
4. Open the video in VLC — subtitles load automatically

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) — `brew install ffmpeg`

## Setup

```bash
git clone https://github.com/yourusername/subtitle-generator
cd subtitle-generator

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

## Usage

```bash
python subtitle_generator.py video.mp4
```

The `.srt` file is saved in the same folder as the video with the same name.

### Options

```
python subtitle_generator.py video.mp4 --model small        # better accuracy
python subtitle_generator.py video.mp4 --translate          # translate to English
python subtitle_generator.py video.mp4 --language ta        # skip auto-detection
python subtitle_generator.py video.mp4 --output ~/subs.srt  # custom output path
```

### All flags

| Flag | Default | Description |
|---|---|---|
| `--model` | `base` | Whisper model size (see below) |
| `--language` | auto | Source language code, e.g. `ta`, `ja`, `es` |
| `--translate` | off | Translate subtitles to English |
| `--output` / `-o` | same as video | Custom `.srt` output path |

### Model sizes

| Model | Size | Speed | Accuracy |
|---|---|---|---|
| `tiny` | ~39 MB | fastest | basic |
| `base` | ~74 MB | fast | good ✓ default |
| `small` | ~244 MB | moderate | better |
| `medium` | ~769 MB | slow | great |
| `large` | ~1550 MB | slowest | best |

Models are downloaded automatically on first use.

## Loading subtitles in VLC

VLC auto-loads the `.srt` if it is in the **same folder** as the video with the **same base name**:

```
movie.mkv  →  movie.srt   ✓ auto-loaded
```

To load manually: **Subtitles → Add Subtitle File…**

## Examples

```bash
# Tamil movie, translate to English
python subtitle_generator.py "example.mkv" --language ta --translate

# Japanese anime, keep original language
python subtitle_generator.py episode01.mkv --model small --language ja

# Video in another folder
python subtitle_generator.py ~/Movies/film.mp4

# Save .srt to a specific location
python subtitle_generator.py film.mp4 --output ~/Desktop/film.srt
```

## Dependencies

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — CTranslate2-based Whisper inference
- [tqdm](https://github.com/tqdm/tqdm) — progress bars
- [ffmpeg](https://ffmpeg.org/) — audio extraction

## License

MIT
