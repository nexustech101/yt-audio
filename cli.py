#!/usr/bin/env python3
from __future__ import annotations

from yt_dlp import YoutubeDL
from registers import CommandRegistry, types as t

from yt_audio import (
    render_start_panel, 
    render_success_panel, 
    normalize_output_dir, 
    require_dependency, 
    build_progress,
    AudioFormat,
    RichYdlLogger, 
    RichDownloadProgress
)

registry = CommandRegistry()


@registry.register(
    "audio",
    description="Extract audio from a YouTube video URL",
    examples=[
        'yt-audio {audio, --audio} "https://www.youtube.com/watch?v=dQw4w9WgXcQ"',
        'yt-audio {audio, --audio} "https://youtu.be/dQw4w9WgXcQ" mp3 ./downloads',
        'yt-audio {audio, --audio} "https://youtu.be/dQw4w9WgXcQ" m4a ./audio --dry-run',
    ],
    default_output="json",
)
@registry.argument("url", type=str, help="YouTube video URL")
@registry.argument(
    "audio_format",
    type=t.Choice(["mp3", "m4a", "wav", "opus", "flac"]),
    default="mp3",
    help="Target audio format",
)
@registry.argument(
    "output_dir",
    type=str,
    default=".",
    help="Directory where the extracted audio file should be saved",
)
@registry.alias("--audio")
@registry.alias("-a")
def extract_audio(
    url: str,
    audio_format: AudioFormat = "mp3",
    output_dir: str = ".",
) -> None:
    """
    Extract audio from a YouTube video.

    Requires:
      - yt-dlp: pip install yt-dlp
      - ffmpeg: system package required for audio conversion
      - rich: pip install rich

    This command owns its Rich presentation, so it returns None.
    That prevents registers.cli from printing a second structured result.
    """
    require_dependency(
        "ffmpeg",
        "Install ffmpeg first. On Ubuntu/Debian: sudo apt install ffmpeg",
    )

    out_dir = normalize_output_dir(output_dir)
    output_template = str(out_dir / "%(title).200s [%(id)s].%(ext)s")

    render_start_panel(
        url=url,
        audio_format=audio_format,
        output_dir=out_dir,
    )

    with build_progress() as progress:
        download_progress = RichDownloadProgress(progress)

        ydl_opts: dict[str, object] = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "logger": RichYdlLogger(),
            "progress_hooks": [download_progress],
            "windowsfilenames": True,
            "restrictfilenames": False,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": "192",
                }
            ],
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

    video_id = str(info.get("id", "unknown"))
    title = str(info.get("title", "unknown"))

    render_success_panel(
        title=title,
        video_id=video_id,
        audio_format=audio_format,
        output_dir=out_dir,
    )

    return None


def main() -> None:
    registry.run(
        shell_title="YouTube Audio CLI",
        shell_description="Extract audio from YouTube videos.",
        shell_usage=True,
    )


if __name__ == "__main__":
    main()