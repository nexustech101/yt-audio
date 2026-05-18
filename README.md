# yt-audio

A small CLI tool for extracting audio from YouTube videos. Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [ffmpeg](https://ffmpeg.org/), with a [Rich](https://github.com/Textualize/rich) terminal interface.

```
╭─────────────────────────── YouTube Audio Extraction ───────────────────────────╮
│ URL     https://www.youtube.com/watch?v=56ZxEmGRt2k                            │
│ Format  wav                                                                    │
│ Output  C:\Users\charl\Documents\Python\yt-audio                               │
╰────────────────────────────────────────────────────────────────────────────────╯
  ✓ Downloaded A Review of ... → converting with ffmpeg… ━━━━━━━━ 13.5/13.5 MB
╭──────────────────────────── Audio Extracted Successfully ───────────────────────╮
│ Status    Complete                                                              │
│ Title     A Review of 10 Most Popular Activation Functions in Neural Networks   │
│ Video ID  56ZxEmGRt2k                                                           │
│ Format    wav                                                                   │
│ Output    C:\Users\charl\Documents\Python\yt-audio                              │
╰─────────────────────────────────────────────────────────────────────────────────╯
```

## Requirements

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/download.html) — must be on your `PATH`

## Installation

```bash
pip install -e .
```

This installs the `yt-audio` entry point along with all Python dependencies (`yt-dlp`, `rich`, `registers`).

## Usage

```
yt-audio audio <url> [format] [output_dir]
```

| Argument     | Description                              | Default |
|--------------|------------------------------------------|---------|
| `url`        | YouTube video URL                        | —       |
| `format`     | Output audio format                      | `mp3`   |
| `output_dir` | Directory to save the extracted audio    | `.`     |

**Supported formats:** `mp3` · `m4a` · `wav` · `opus` · `flac`

The command can also be invoked via `--audio` or `-a`.

### Examples

```bash
# Extract as mp3 (default) into the current directory
yt-audio audio "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Extract as wav
yt-audio --audio "https://youtu.be/dQw4w9WgXcQ" wav

# Extract as flac into a specific directory
yt-audio audio "https://youtu.be/dQw4w9WgXcQ" flac ./audio

# Preview what would happen without downloading
yt-audio audio "https://youtu.be/dQw4w9WgXcQ" mp3 ./audio --dry-run
```

### Dry run

Pass `--dry-run` to preview the resolved output path and filename template without downloading anything.

```
╭──────────────────────────────── Dry Run Preview ───────────────────────────────╮
│ Mode      Dry Run                                                               │
│ URL       https://www.youtube.com/watch?v=dQw4w9WgXcQ                          │
│ Format    mp3                                                                   │
│ Output    C:\Users\charl\audio                                                  │
│ Template  C:\Users\charl\audio\%(title).200s [%(id)s].%(ext)s                   │
╰────────────────────────────────────────────────────────────────────────────────╯
```

## Output naming

Files are saved as:

```
<title> [<video_id>].<ext>
```

Titles are capped at 200 characters and Windows-safe filename characters are enforced automatically.

## License

MIT
