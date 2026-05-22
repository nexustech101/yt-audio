from __future__ import annotations

from yt_audio import VideoQuality, build_video_format


def test_video_quality_values_are_cli_values() -> None:
    assert [quality.value for quality in VideoQuality] == [
        "best",
        "2160p",
        "1440p",
        "1080p",
        "720p",
        "480p",
        "360p",
        "worst",
    ]


def test_height_quality_caps_format_selector() -> None:
    assert build_video_format(VideoQuality.P720) == (
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
        "bestvideo[height<=720]+bestaudio/"
        "best[height<=720][ext=mp4]/"
        "best[height<=720]"
    )


def test_best_quality_prefers_mp4_video_and_m4a_audio() -> None:
    assert build_video_format(VideoQuality.BEST).startswith(
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
    )
