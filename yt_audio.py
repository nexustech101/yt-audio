#!/usr/bin/env python3
from __future__ import annotations

import shutil
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

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

console = Console(force_terminal=True)

AudioFormat = Literal["mp3", "m4a", "wav", "opus", "flac"]


class VideoQuality(StrEnum):
    BEST = "best"
    P2160 = "2160p"
    P1440 = "1440p"
    P1080 = "1080p"
    P720 = "720p"
    P480 = "480p"
    P360 = "360p"
    WORST = "worst"


def build_video_format(quality: VideoQuality) -> str:
    if quality is VideoQuality.BEST:
        return (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo+bestaudio/"
            "best[ext=mp4]/best"
        )

    if quality is VideoQuality.WORST:
        return (
            "worstvideo[ext=mp4]+worstaudio[ext=m4a]/"
            "worstvideo+worstaudio/"
            "worst[ext=mp4]/worst"
        )

    max_height = int(quality.value.removesuffix("p"))
    return (
        f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={max_height}]+bestaudio/"
        f"best[height<={max_height}][ext=mp4]/"
        f"best[height<={max_height}]"
    )


class RichDownloadProgress:
    """
    Bridges yt-dlp's progress hook interface into Rich Progress.

    yt-dlp calls this object with dictionaries containing download status,
    byte counts, filename metadata, and postprocessing state.
    """

    def __init__(
        self,
        progress: Progress,
        postprocess_label: str = "converting with ffmpeg",
    ) -> None:
        self.progress = progress
        self.postprocess_label = postprocess_label
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
                    f"[dim]→[/dim] [cyan]{self.postprocess_label}…[/cyan]"
                ),
            )

    def _get_task(self, task_id: TaskID) -> Any | None:
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


def resolve_output_dir(output_dir: str) -> Path:
    return Path(output_dir).expanduser().resolve()


def normalize_output_dir(output_dir: str) -> Path:
    path = resolve_output_dir(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_start_panel(url: str, audio_format: str, output_dir: Path) -> None:
    render_download_start_panel(
        title="YouTube Audio Extraction",
        url=url,
        label="Format",
        value=audio_format,
        output_dir=output_dir,
    )


def render_video_start_panel(url: str, quality: VideoQuality, output_dir: Path) -> None:
    render_download_start_panel(
        title="YouTube Video Download",
        url=url,
        label="Quality",
        value=quality.value,
        output_dir=output_dir,
    )


def render_download_start_panel(
    title: str,
    url: str,
    label: str,
    value: str,
    output_dir: Path,
) -> None:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()

    table.add_row("URL", url)
    table.add_row(label, value)
    table.add_row("Output", str(output_dir))

    console.print(
        Panel(
            table,
            title=f"[bold]{title}[/bold]",
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


def render_video_success_panel(
    title: str,
    video_id: str,
    quality: VideoQuality,
    output_dir: Path,
) -> None:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold green", no_wrap=True)
    table.add_column()

    table.add_row("Status", "Complete")
    table.add_row("Title", title)
    table.add_row("Video ID", video_id)
    table.add_row("Quality", quality.value)
    table.add_row("Output", str(output_dir))

    console.print(
        Panel(
            table,
            title="[bold green]Video Saved Successfully[/bold green]",
            border_style="green",
        )
    )


def render_dry_run_panel(
    mode: str,
    url: str,
    label: str,
    value: str,
    output_dir: Path,
    output_template: str,
) -> None:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()

    table.add_row("Mode", "Dry Run")
    table.add_row("URL", url)
    table.add_row(label, value)
    table.add_row("Output", str(output_dir))
    table.add_row("Template", output_template)

    console.print(
        Panel(
            table,
            title=f"[bold]{mode} Preview[/bold]",
            border_style="cyan",
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
