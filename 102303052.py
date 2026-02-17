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
    # Allow help to work
    if "-h" in argv or "--help" in argv:
        parser = build_parser()
        return parser.parse_args(argv)

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
    if output_path.suffix.lower() not in [".mp3", ".mp4"]:
        raise ValueError("OutputFileName must end with .mp3 (or .mp4 for video)")
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
    from googleapiclient.discovery import build
    
    print(f"[SEARCH] Searching YouTube for: {singer_name}")
    
    # Get YouTube API key from environment
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    if not youtube_api_key:
        raise RuntimeError("YOUTUBE_API_KEY environment variable not set. Please set it in your deployment config.")
    
    print(f"[API] Using YouTube Data API to search")
    try:
        youtube = build("youtube", "v3", developerKey=youtube_api_key)
        # Request both id and snippet so we always get videoId
        search_request = youtube.search().list(
            q=singer_name,
            part="id,snippet",
            type="video",
            maxResults=number_of_videos,
            relevanceLanguage="en",
            order="relevance",
        )
        search_response = search_request.execute()
    except Exception as e:
        print(f"[ERROR] YouTube API search failed: {e}")
        raise RuntimeError(f"YouTube API error: {e}")
    
    video_ids = []
    for item in search_response.get("items", []):
        vid = item.get("id", {}).get("videoId")
        if vid:
            video_ids.append(vid)
    
    if not video_ids:
        raise RuntimeError(f"No videos found for {singer_name} using YouTube API")
    
    print(f"[FOUND] Found {len(video_ids)} videos, downloading...")
    
    ydl_options = {
        # Prefer formats that usually work without JavaScript signature extraction.
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "quiet": False,
        "no_warnings": False,
        "ignoreerrors": True,
        "noplaylist": True,
        "outtmpl": str(download_dir / "%(title).80s-%(id)s.%(ext)s"),
        "socket_timeout": 10,
        "connect_timeout": 10,
        "retries": 2,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    }

    print(f"[DOWNLOAD] Starting download with yt_dlp")
    try:
        with YoutubeDL(ydl_options) as ydl:
            for i, vid_id in enumerate(video_ids, 1):
                url = f"https://www.youtube.com/watch?v={vid_id}"
                print(f"[DOWNLOAD] {i}/{len(video_ids)}: {url}")
                try:
                    ydl.extract_info(url, download=True)
                except Exception as e:
                    print(f"[SKIP] Failed to download {vid_id}: {e}")
                    continue
        print(f"[SUCCESS] yt_dlp completed")
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        raise

    downloaded = sorted(
        [path for path in download_dir.iterdir() if path.is_file()],
        key=lambda path: path.stat().st_mtime,
    )
    print(f"[RESULT] Found {len(downloaded)} downloaded files")
    if len(downloaded) < number_of_videos:
        if len(downloaded) == 0:
             raise RuntimeError(
                 f"Could not download any videos for {singer_name}. "
                 "yt_dlp could not extract playable streams from YouTube."
             )
        print(f"Warning: Only downloaded {len(downloaded)} videos.")
    
    print(f"[PROGRESS] Downloaded {len(downloaded)} videos")
    return downloaded[:number_of_videos]


def trim_clip(audio_clip, end_time: float):
    # Handle different moviepy versions
    try:
        return audio_clip.subclipped(0, end_time)
    except AttributeError:
        return audio_clip.subclip(0, end_time)


def create_merged_video(files: List[Path], audio_duration: int, output_path: Path) -> None:
    print("Processing clips...")
    try:
        from moviepy.editor import AudioFileClip, concatenate_audioclips, ColorClip, ImageClip
    except ImportError:
        try:
           from moviepy import AudioFileClip, concatenate_audioclips, ColorClip, ImageClip
        except ImportError:
            raise ImportError("moviepy is not installed correctly.")

    clips = []
    try:
        for file_path in files:
            try:
                clip = AudioFileClip(str(file_path))
                duration = min(float(audio_duration), clip.duration)
                sub = trim_clip(clip, duration)
                clips.append(sub)
            except Exception as e:
                print(f"Skipping file {file_path.name} due to error: {e}")
                continue

        if not clips:
            raise RuntimeError("No valid audio clips to merge.")

        print(f"Merging {len(clips)} audio clips...")
        print(f"[PROGRESS] Merging {len(clips)} audio clips...")
        final_audio = concatenate_audioclips(clips)
        
        # Create video
        # Create video
        print("Creating video file...")
        print("[PROGRESS] Creating video file...")
        # Use a simple color background (blue-ish) or generate one
        # 720p resolution
        try:
             video = ColorClip(size=(1280, 720), color=(14, 165, 233), duration=final_audio.duration)
        except Exception:
             # Fallback for older moviepy
             video = ColorClip(size=(1280, 720), col=(14, 165, 233), duration=final_audio.duration)
             
        video = video.set_audio(final_audio)
        
        # Determine output format. If extension is .mp3, we still force .mp4 content but name it .mp3? 
        # Requirement said output file must be .mp3 in CLI args. 
        # But user wants video preview.
        # Strategy: CLI still creates requested file (MP3). 
        # BUT for the web app, we might need a separate function.
        # Actually, let's keep CLI doing standard MP3 for the assignment requirement.
        # And add a NEW function for the web app to trigger video creation.
        
        # WAIT: The assignment requires Program 1 to make an output file. 
        # I shouldn't break the CLI contract. 
        # I will modify this function to support BOTH if needed, or keeping it MP3 for CLI.
        
        # Reverting to MP3 for standard execution, but allowing MP4 if extension is .mp4
        if output_path.suffix.lower() == ".mp4":
            video.write_videofile(
                str(output_path),
                fps=1, # Low FPS for static image to save size/time
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )
        else:
            final_audio.write_audiofile(
                str(output_path),
                codec="libmp3lame",
                bitrate="192k",
                logger=None,
            )

        final_audio.close()
        video.close()

    finally:
        for clip in clips:
             try: clip.close() 
             except: pass


def run_mashup(singer_name: str, number_of_videos: int, audio_duration: int, output_path: Path) -> Path:
    configure_ffmpeg()
    working_dir = Path(tempfile.mkdtemp(prefix="mashup_cli_"))
    download_dir = working_dir / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    try:
        video_files = download_videos(singer_name, number_of_videos, download_dir)
        create_merged_video(video_files, audio_duration, output_path)
        return output_path
    finally:
        try:
             shutil.rmtree(working_dir, ignore_errors=True)
        except Exception:
             pass


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
