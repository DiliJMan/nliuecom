#!/usr/bin/env python3
"""One entry point for setup, development and tests. Works the same on Windows and Linux.

    python scripts/run.py setup --email you@example.com   # install, migrate, create the first admin
    python scripts/run.py dev                              # API on :8000, web app on :5173 (watching files)
    python scripts/run.py serve                            # built web app, no file watching
    python scripts/run.py test                             # backend tests, lint, frontend checks
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"
VENV = BACKEND / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"\n$ {' '.join(cmd)}   (in {cwd.relative_to(ROOT)})", flush=True)
    subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, check=True)


def npm() -> str:
    found = shutil.which("npm")
    if not found:
        sys.exit("Node.js 22.17 or newer is required (npm was not found). See https://nodejs.org")
    return found


def ensure_backend_env() -> None:
    if VENV_PYTHON.exists():
        return
    if sys.version_info < (3, 12):
        sys.exit("Python 3.12 or newer is required.")
    run([sys.executable, "-m", "venv", str(VENV)], BACKEND)
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"] + project["dependency-groups"]["dev"]
    run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", *dependencies], BACKEND)


def manage(*args: str, env: dict[str, str] | None = None) -> None:
    run([str(VENV_PYTHON), "manage.py", *args], BACKEND, env)


def setup(args: argparse.Namespace) -> None:
    ensure_backend_env()
    run([npm(), "install"], FRONTEND)
    manage("migrate")
    if args.email:
        manage("bootstrap", "--email", args.email)
    print("\nSetup complete. Start the app with: python scripts/run.py dev")


def _wait_and_stop(processes: list[subprocess.Popen]) -> None:
    try:
        while all(p.poll() is None for p in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


def dev(_: argparse.Namespace) -> None:
    ensure_backend_env()
    manage("migrate", "--noinput")
    backend_env = {**os.environ, "NLIUE_TRUST_FORWARDED_FOR": "1", "NLIUE_DEBUG": "1"}
    processes = [
        subprocess.Popen(
            [str(VENV_PYTHON), "manage.py", "runserver", "127.0.0.1:8000"], cwd=BACKEND, env=backend_env
        ),
        subprocess.Popen([npm(), "run", "dev", "--", "--host", "127.0.0.1"], cwd=FRONTEND),
    ]
    print("\nWeb app: http://127.0.0.1:5173   API: http://127.0.0.1:8000 (reached through the web app)")
    _wait_and_stop(processes)


def serve(args: argparse.Namespace) -> None:
    """Production-style local run: built web app plus the API, no file watching."""
    ensure_backend_env()
    port = args.port
    origin = f"http://127.0.0.1:{port}"
    run([npm(), "run", "build"], FRONTEND, {"NLIUE_WEB_ORIGIN": origin})
    manage("migrate", "--noinput")
    web_env = {
        **os.environ,
        "HOST": "127.0.0.1",
        "PORT": str(port),
        "BACKEND_URL": "http://127.0.0.1:8000",
        # The adapter's default of 512 KB would reject evidence uploads.
        "BODY_SIZE_LIMIT": "40M",
    }
    api_env = {**os.environ, "NLIUE_TRUST_FORWARDED_FOR": "1"}
    processes = [
        subprocess.Popen(
            [str(VENV_PYTHON), "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            cwd=BACKEND,
            env=api_env,
        ),
        subprocess.Popen(["node", "build"], cwd=FRONTEND, env=web_env),
    ]
    print(f"\nOpen {origin}")
    _wait_and_stop(processes)


def test(_: argparse.Namespace) -> None:
    ensure_backend_env()
    run([str(VENV_PYTHON), "-m", "ruff", "check", "."], BACKEND)
    run([str(VENV_PYTHON), "-m", "pytest"], BACKEND)
    run([npm(), "run", "check"], FRONTEND)
    run([npm(), "test"], FRONTEND)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    setup_parser = commands.add_parser("setup")
    setup_parser.add_argument("--email", help="Create the first administrator with this address")
    setup_parser.set_defaults(handler=setup)
    commands.add_parser("dev").set_defaults(handler=dev)
    serve_parser = commands.add_parser("serve")
    serve_parser.add_argument("--port", type=int, default=5173)
    serve_parser.set_defaults(handler=serve)
    commands.add_parser("test").set_defaults(handler=test)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
