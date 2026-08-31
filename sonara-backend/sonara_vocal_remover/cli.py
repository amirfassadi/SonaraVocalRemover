"""
CLI entry point.

    python -m sonara_vocal_remover input/song.wav
    python -m sonara_vocal_remover "https://example.com/audio/song.mp3" --device cuda

Builds the appropriate InputSource (LocalFileSource for a local path,
UrlSource for http(s)://...) and calls the same VocalRemovalService.process()
used by the Python API — the CLI and the Python API share one code path.
"""

import argparse
import sys
from urllib.parse import urlparse

from sonara_vocal_remover.config import DEFAULT_DEVICE, DEFAULT_MODEL
from sonara_vocal_remover.errors import SonaraError
from sonara_vocal_remover.service import VocalRemovalService
from sonara_vocal_remover.sources import LocalFileSource, UrlSource


def _looks_like_url(value: str) -> bool:
    return urlparse(value).scheme in ("http", "https")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sonara_vocal_remover",
        description="Remove vocals from a music track, producing vocals.wav and instrumental.wav.",
    )
    parser.add_argument("input", help="Local file path or direct audio URL")
    parser.add_argument(
        "--output", "-o", default="output", help="Output directory (default: ./output)"
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default=DEFAULT_DEVICE,
        help="Processing device (default: %(default)s)",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help="Separation model variant (default: %(default)s)"
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    source = UrlSource(args.input) if _looks_like_url(args.input) else LocalFileSource(args.input)

    service = VocalRemovalService(model=args.model, device=args.device)

    try:
        result = service.process(source=source, output_dir=args.output)
    except SonaraError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Print results: support both legacy vocal/instrumental and arbitrary stems
    if result.stems:
        for stem_name, stem_path in sorted(result.stems.items()):
            print(f"{stem_name.capitalize():20} stem saved to: {stem_path}")
    else:
        # Fallback for older/legacy results (shouldn't happen with current code)
        print(f"Vocals stem saved to:       {result.vocals_path}")
        print(f"Instrumental stem saved to: {result.instrumental_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
