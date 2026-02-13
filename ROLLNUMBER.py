import argparse
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mashup CLI: download videos, extract audio, trim, and merge."
    )
    parser.add_argument("singer_name", type=str, help="Singer name to search on YouTube")
    parser.add_argument("number_of_videos", type=int, help="Number of videos (>10)")
    parser.add_argument("audio_duration", type=int, help="Duration in seconds to trim from each audio (>20)")
    parser.add_argument("output_file", type=str, help="Output merged audio file name, e.g., output.mp3")
    return parser.parse_args()


def validate_inputs(args: argparse.Namespace) -> None:
    if args.number_of_videos <= 10:
        raise ValueError("number_of_videos must be greater than 10")
    if args.audio_duration <= 20:
        raise ValueError("audio_duration must be greater than 20 seconds")


if __name__ == "__main__":
    try:
        cli_args = parse_args()
        validate_inputs(cli_args)

        # TODO: Implement download -> convert -> trim -> merge workflow.
        print(
            "Starter created. Implement mashup steps for:",
            cli_args.singer_name,
            cli_args.number_of_videos,
            cli_args.audio_duration,
            cli_args.output_file,
        )
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)