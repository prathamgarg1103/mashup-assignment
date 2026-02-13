import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List

USAGE_LINE = (
    "python 102303052.py <SingerName> <NumberOfVideos> <AudioDuration> <OutputFileName>"
)


class MashupArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def build_parser() -> MashupArgumentParser:
    parser = MashupArgumentParser(
        description=(
            "Download YouTube videos for a singer, take first Y seconds of each "
            "audio, and merge into one MP3."
        ),
        add_help=True,
    )
    parser.add_argument("singer_name", type=str, help="Singer name to search on YouTube")
    parser.add_argument("number_of_videos", type=int, help="Number of videos to download (>10)")
    parser.add_argument("audio_duration", type=int, help="Duration per audio clip in seconds (>20)")
    parser.add_argument("output_file", type=str, help="Output file name (must end with .mp3)")
    return parser


def parse_args(argv: List[str]) -> argparse.Namespace:
    if len(argv) != 4:
        raise ValueError(
            "Incorrect number of parameters.\n"
            f"Usage: {USAGE_LINE}"
        )
    parser = build_parser()
    return parser.parse_args(argv)


def validate_inputs(args: argparse.Namespace) -> Path:
    singer = args.singer_name.strip()
    if not singer:
        raise ValueError("Singer name must not be empty.")
    if args.number_of_videos <= 10:
        raise ValueError("NumberOfVideos must be greater than 10.")
    if args.audio_duration <= 20:
        raise ValueError("AudioDuration must be greater than 20 seconds.")

    output_path = Path(args.output_file).expanduser()
    if output_path.suffix.lower() != ".mp3":
        raise ValueError("OutputFileName must end with .mp3")
    if output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path.resolve()


def configure_ffmpeg() -> None:
    import imageio_ffmpeg

    ffmpeg_binary = imageio_ffmpeg.get_ffmpeg_exe()
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_binary
    os.environ["FFMPEG_BINARY"] = ffmpeg_binary
    try:
        from moviepy.config import change_settings

        change_settings({"FFMPEG_BINARY": ffmpeg_binary})
    except Exception:
        pass


def download_videos(singer_name: str, number_of_videos: int, download_dir: Path) -> List[Path]:
    from yt_dlp import YoutubeDL

    query = f"ytsearch{number_of_videos}:{singer_name} songs"
    ydl_options = {
        "format": "best[height<=360][ext=mp4]/best[height<=360]/worst[ext=mp4]/worst",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "restrictfilenames": True,
        "outtmpl": str(download_dir / "%(title).80s-%(id)s.%(ext)s"),
    }

    with YoutubeDL(ydl_options) as ydl:
        ydl.extract_info(query, download=True)

    downloaded = sorted(
        [path for path in download_dir.iterdir() if path.is_file()],
        key=lambda path: path.stat().st_mtime,
    )
    if len(downloaded) < number_of_videos:
        raise RuntimeError(
            f"Could only download {len(downloaded)} videos, requested {number_of_videos}. "
            "Try a more popular singer name or run again."
        )
    return downloaded[:number_of_videos]


def trim_clip(audio_clip, end_time: float):
    if hasattr(audio_clip, "subclip"):
        return audio_clip.subclip(0, end_time)
    return audio_clip.subclipped(0, end_time)


def create_merged_audio(video_files: List[Path], audio_duration: int, output_path: Path) -> None:
    try:
        from moviepy import VideoFileClip, concatenate_audioclips
    except ImportError:
        from moviepy.editor import VideoFileClip, concatenate_audioclips

    video_clips = []
    audio_snippets = []
    merged_audio = None
    try:
        for video_file in video_files:
            video_clip = VideoFileClip(str(video_file))
            video_clips.append(video_clip)
            if video_clip.audio is None:
                continue

            available_duration = float(video_clip.audio.duration or 0.0)
            clip_end = min(float(audio_duration), available_duration)
            if clip_end <= 0:
                continue

            snippet = trim_clip(video_clip.audio, clip_end)
            audio_snippets.append(snippet)

        if not audio_snippets:
            raise RuntimeError("No valid audio clips found in downloaded videos.")

        merged_audio = concatenate_audioclips(audio_snippets)
        merged_audio.write_audiofile(
            str(output_path),
            codec="mp3",
            bitrate="192k",
            logger=None,
        )
    finally:
        if merged_audio is not None:
            merged_audio.close()
        for snippet in audio_snippets:
            try:
                snippet.close()
            except Exception:
                pass
        for clip in video_clips:
            try:
                clip.close()
            except Exception:
                pass


def run_mashup(singer_name: str, number_of_videos: int, audio_duration: int, output_path: Path) -> Path:
    configure_ffmpeg()
    working_dir = Path(tempfile.mkdtemp(prefix="mashup_cli_"))
    download_dir = working_dir / "videos"
    download_dir.mkdir(parents=True, exist_ok=True)
    try:
        video_files = download_videos(singer_name, number_of_videos, download_dir)
        create_merged_audio(video_files, audio_duration, output_path)
        return output_path
    finally:
        shutil.rmtree(working_dir, ignore_errors=True)


def main(argv: List[str]) -> int:
    try:
        args = parse_args(argv)
        output_path = validate_inputs(args)
        final_file = run_mashup(
            singer_name=args.singer_name.strip(),
            number_of_videos=args.number_of_videos,
            audio_duration=args.audio_duration,
            output_path=output_path,
        )
        print(f"Mashup created successfully: {final_file}")
        return 0
    except ValueError as exc:
        print(f"Input error: {exc}")
        print(f"Usage: {USAGE_LINE}")
        return 1
    except Exception as exc:
        print(f"Execution error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
