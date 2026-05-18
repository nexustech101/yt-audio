#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Literal

from registers import CommandRegistry, types as t
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from yt_dlp import YoutubeDL

registry = CommandRegistry()
console = Console(force_terminal=True)

AudioFormat = Literal["mp3", "m4a", "wav", "opus", "flac"]


class RichDownloadProgress:
    """
    Bridges yt-dlp's progress hook interface into Rich Progress.

    yt-dlp calls this object with dictionaries containing download status,
    byte counts, filename metadata, and postprocessing state.
    """

    def __init__(self, progress: Progress) -> None:
        self.progress = progress
        self.task_id: TaskID | None = None
        self.current_filename: str | None = None

    def __call__(self, event: dict[str, Any]) -> None:
        status = event.get("status")

        if status == "downloading":
            self._handle_downloading(event)
            return

        if status == "finished":
            self._handle_finished(event)
            return

        if status == "error":
            if self.task_id is not None:
                self.progress.update(
                    self.task_id,
                    description="[bold red]✗ Download failed[/bold red]",
                )
            else:
                self.progress.print("[bold red]Download failed.[/bold red]")

    @staticmethod
    def _truncate(name: str, length: int = 12) -> str:
        return name if len(name) <= length else name[:length] + "..."

    def _handle_downloading(self, event: dict[str, Any]) -> None:
        filename = str(event.get("filename") or "download")
        display_name = self._truncate(Path(filename).name)

        total = event.get("total_bytes") or event.get("total_bytes_estimate")
        downloaded = int(event.get("downloaded_bytes") or 0)

        if self.task_id is None or self.current_filename != filename:
            self.current_filename = filename
            self.task_id = self.progress.add_task(
                f"[cyan]Downloading[/cyan] {display_name}",
                total=int(total) if total else None,
                completed=downloaded,
            )
            return

        if total:
            self.progress.update(
                self.task_id,
                total=int(total),
                completed=downloaded,
            )
        else:
            self.progress.update(
                self.task_id,
                completed=downloaded,
            )

    def _handle_finished(self, event: dict[str, Any]) -> None:
        filename = self._truncate(Path(str(event.get("filename") or "download")).name)

        if self.task_id is not None:
            task = self._get_task(self.task_id)
            if task is not None and task.total is not None:
                self.progress.update(self.task_id, completed=task.total)

            self.progress.update(
                self.task_id,
                description=(
                    f"[green]✓ Downloaded[/green] {filename} "
                    f"[dim]→[/dim] [cyan]converting with ffmpeg…[/cyan]"
                ),
            )

    def _get_task(self, task_id: TaskID):
        for task in self.progress.tasks:
            if task.id == task_id:
                return task
        return None


class RichYdlLogger:
    """Routes yt-dlp log messages through Rich, preventing direct stderr writes
    that would break Rich's live cursor tracking."""

    def debug(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        console.print(f"[bold red]Error:[/bold red] {msg}")


def require_dependency(command: str, install_hint: str) -> None:
    if shutil.which(command) is None:
        raise RuntimeError(f"Missing dependency: {command}. {install_hint}")


def normalize_output_dir(output_dir: str) -> Path:
    path = Path(output_dir).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_start_panel(url: str, audio_format: str, output_dir: Path) -> None:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()

    table.add_row("URL", url)
    table.add_row("Format", audio_format)
    table.add_row("Output", str(output_dir))

    console.print(
        Panel(
            table,
            title="[bold]YouTube Audio Extraction[/bold]",
            border_style="cyan",
        )
    )


def render_success_panel(
    title: str,
    video_id: str,
    audio_format: str,
    output_dir: Path,
) -> None:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold green", no_wrap=True)
    table.add_column()

    table.add_row("Status", "Complete")
    table.add_row("Title", title)
    table.add_row("Video ID", video_id)
    table.add_row("Format", audio_format)
    table.add_row("Output", str(output_dir))

    console.print(
        Panel(
            table,
            title="[bold green]Audio Extracted Successfully[/bold green]",
            border_style="green",
        )
    )


def build_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
        refresh_per_second=8,
    )


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