#!/usr/bin/env python3
from __future__ import annotations

from yt_dlp import YoutubeDL  # type: ignore[import-untyped]
from registers import CommandRegistry, types as t

from yt_audio import (
    AudioFormat,
    RichDownloadProgress,
    RichYdlLogger,
    VideoQuality,
    build_progress,
    build_video_format,
    normalize_output_dir,
    render_dry_run_panel,
    render_start_panel,
    render_success_panel,
    render_video_start_panel,
    render_video_success_panel,
    require_dependency,
    resolve_output_dir,
)

registry = CommandRegistry()


@registry.register(
    "audio",
    description="Extract audio from a YouTube video URL",
    examples=[
        'yt-audio {audio, --audio} "https://www.youtube.com/watch?v=dQw4w9WgXcQ"',
        'yt-audio {audio, --audio} "https://youtu.be/dQw4w9WgXcQ" mp3 ./downloads/audio',
        'yt-audio {audio, --audio} "https://youtu.be/dQw4w9WgXcQ" m4a ./downloads/audio --dry-run',
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
@registry.argument(
    "dry_run",
    type=bool,
    default=False,
    help="Show the resolved download settings without downloading",
)
@registry.alias("--audio")
@registry.alias("-a")
def extract_audio(
    url: str,
    audio_format: AudioFormat = "mp3",
    output_dir: str = ".",
    dry_run: bool = False,
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
    out_dir = resolve_output_dir(output_dir) if dry_run else normalize_output_dir(output_dir)
    output_template = str(out_dir / "%(title).200s [%(id)s].%(ext)s")

    if dry_run:
        render_dry_run_panel(
            mode="Audio Extraction",
            url=url,
            label="Format",
            value=audio_format,
            output_dir=out_dir,
            output_template=output_template,
        )
        return None

    require_dependency(
        "ffmpeg",
        "Install ffmpeg first. On Ubuntu/Debian: sudo apt install ffmpeg",
    )

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


@registry.register(
    "video",
    description="Save the full video from a YouTube URL",
    examples=[
        'yt-audio {video, --video} "https://www.youtube.com/watch?v=dQw4w9WgXcQ"',
        'yt-audio {video, --video} "https://youtu.be/dQw4w9WgXcQ" 1080p ./videos',
        'yt-audio {video, --video} "https://youtu.be/dQw4w9WgXcQ" best ./videos --dry-run',
    ],
    default_output="json",
)
@registry.argument("url", type=str, help="YouTube video URL")
@registry.argument(
    "quality",
    type=t.Enum(VideoQuality),
    default=VideoQuality.BEST,
    help="Target video quality",
)
@registry.argument(
    "output_dir",
    type=str,
    default=".",
    help="Directory where the video file should be saved",
)
@registry.argument(
    "dry_run",
    type=bool,
    default=False,
    help="Show the resolved download settings without downloading",
)
@registry.alias("--video")
@registry.alias("-v")
def save_video(
    url: str,
    quality: VideoQuality = VideoQuality.BEST,
    output_dir: str = ".",
    dry_run: bool = False,
) -> None:
    """
    Save a full YouTube video.

    Requires:
      - yt-dlp: pip install yt-dlp
      - ffmpeg: system package required when yt-dlp merges video and audio streams
      - rich: pip install rich

    This command owns its Rich presentation, so it returns None.
    That prevents registers.cli from printing a second structured result.
    """
    out_dir = resolve_output_dir(output_dir) if dry_run else normalize_output_dir(output_dir)
    output_template = str(out_dir / "%(title).200s [%(id)s].%(ext)s")

    if dry_run:
        render_dry_run_panel(
            mode="Video Download",
            url=url,
            label="Quality",
            value=quality.value,
            output_dir=out_dir,
            output_template=output_template,
        )
        return None

    require_dependency(
        "ffmpeg",
        "Install ffmpeg first. On Ubuntu/Debian: sudo apt install ffmpeg",
    )

    render_video_start_panel(
        url=url,
        quality=quality,
        output_dir=out_dir,
    )

    with build_progress() as progress:
        download_progress = RichDownloadProgress(progress, postprocess_label="merging with ffmpeg")

        ydl_opts: dict[str, object] = {
            "format": build_video_format(quality),
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "logger": RichYdlLogger(),
            "progress_hooks": [download_progress],
            "windowsfilenames": True,
            "restrictfilenames": False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

    video_id = str(info.get("id", "unknown"))
    title = str(info.get("title", "unknown"))

    render_video_success_panel(
        title=title,
        video_id=video_id,
        quality=quality,
        output_dir=out_dir,
    )

    return None


def main() -> None:
    registry.run(
        shell_title="YouTube Audio CLI",
        shell_description="Extract audio from YouTube videos or save full videos.",
        shell_usage=True,
    )


if __name__ == "__main__":
    main()
