"""Publish the tested model package using the current Hugging Face CLI login."""
import argparse
import subprocess
from pathlib import Path
from build_model import build

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', default='larkooo/veto')
    args = parser.parse_args()
    subprocess.run(['hf', 'auth', 'whoami'], check=True)
    target = build()
    subprocess.run(['npm', 'test'], cwd=ROOT, check=True)
    subprocess.run(['npm', 'run', 'test:model'], cwd=ROOT, check=True)
    subprocess.run(['hf', 'repos', 'create', args.repo, '--type', 'model', '--public', '--exist-ok'], check=True)
    subprocess.run(['hf', 'upload', args.repo, str(target), '.', '--commit-message', 'Publish Veto local model and runtime'], check=True)


if __name__ == '__main__':
    main()
