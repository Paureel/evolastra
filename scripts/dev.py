from __future__ import annotations

import argparse
import shutil
import signal
import subprocess
import sys
import time
import urllib.request


def wait_for_api(timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=1):  # noqa: S310
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError("API did not become ready")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm is required")
    processes = [
        subprocess.Popen(  # noqa: S603 - fixed interpreter and module
            [
                sys.executable,
                "-m",
                "uvicorn",
                "asterism_api.main:app",
                "--app-dir",
                "apps/api",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ]
        ),  # noqa: S603
        subprocess.Popen([npm, "--prefix", "apps/web", "run", "dev"]),  # noqa: S603
    ]
    try:
        wait_for_api()
        if args.demo:
            request = urllib.request.Request(
                "http://127.0.0.1:8000/api/v1/demo/start?speed=6", data=b"{}", method="POST"
            )
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                print(response.read().decode("utf-8"))
        print("Asterism Observatory: http://127.0.0.1:5173")
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
