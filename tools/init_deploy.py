"""Create private deployment configuration without overwriting existing credentials."""
import argparse
import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlsplit


def initialize(destination, origin, device="cpu", torch_index_url=None):
    if device not in ("cpu", "cuda"):
        raise ValueError("Device must be cpu or cuda.")
    if torch_index_url is None:
        if device == "cuda":
            raise ValueError("CUDA requires an explicit --torch-index-url matched to the host driver.")
        torch_index_url = "https://download.pytorch.org/whl/cpu"
    expected = r"https://download\.pytorch\.org/whl/cu[0-9]+" if device == "cuda" else r"https://download\.pytorch\.org/whl/cpu"
    if not re.fullmatch(expected, torch_index_url):
        raise ValueError("Use the official PyTorch wheel index matching the selected device.")

    url = urlsplit(origin)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.path not in ('', '/') or url.query or url.fragment
            or any(c.isspace() for c in origin) or any(c in origin for c in '\n\r#$')):
        raise ValueError('Use an HTTPS origin, for example https://karaoke.example.com, without a path.')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = (f'PUBLIC_ORIGIN={origin.rstrip("/")}\n'
               f'SONARA_API_TOKEN={secrets.token_hex(32)}\n'
               f'SONARA_SESSION_SECRET={secrets.token_hex(32)}\n'
               f'SONARA_PASSWORD={secrets.token_hex(16)}\n'
               f'SONARA_DEFAULT_MODEL=bs_roformer_viperx\nSONARA_DEVICE={device}\n'
               f'TORCH_INDEX_URL={torch_index_url}\n'
               'SONARA_CPU_THREADS=2\nSONARA_JOB_TIMEOUT=600\nSONARA_PORT=3000\n')
    with os.fdopen(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
        output.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--torch-index-url', help='Official wheel index; required for CUDA after checking the host driver')
    parser.add_argument('--output', type=Path, default=Path('deploy/.env'))
    args = parser.parse_args()
    try:
        initialize(args.output, args.origin, args.device, args.torch_index_url)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f'Created {args.output}. Browser username: sonara. Password is in that file.')

if __name__ == '__main__':
    main()
