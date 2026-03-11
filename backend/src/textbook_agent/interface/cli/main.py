import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Textbook Generation Agent - Generate personalized textbooks from learner profiles"
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="Path to learner profile JSON file",
    )
    parser.add_argument(
        "--provider",
        default="claude",
        choices=["claude", "openai"],
        help="LLM provider to use (default: claude)",
    )
    parser.add_argument(
        "--depth",
        choices=["survey", "standard", "deep"],
        help="Override depth from profile",
    )
    parser.add_argument(
        "--output",
        default="outputs/",
        help="Output directory (default: outputs/)",
    )
    parser.add_argument(
        "--format",
        default="html",
        choices=["html"],
        help="Output format (default: html)",
    )

    args = parser.parse_args()

    print(f"Textbook Agent v0.1.0")
    print(f"Profile: {args.profile}")
    print(f"Provider: {args.provider}")
    print(f"Output: {args.output}")
    print("Not yet implemented - skeleton only")
    sys.exit(0)


if __name__ == "__main__":
    main()
