import subprocess
import sys


def main():
    cmd = ["python", "manage.py", "runserver", "0.0.0.0:8000"]
    subprocess.run(cmd)


def collectstatic():
    # Get last arg (if any)
    verbosity = sys.argv[1] if len(sys.argv) > 1 else "1"

    # Check if it looks like a digit; fallback to "1"
    if not verbosity.isdigit():
        print(f"Warning: invalid verbosity value '{verbosity}', defaulting to 1")
        verbosity = "1"

    cmd = [
        "python",
        "manage.py",
        "collectstatic",
        "--noinput",
        "--verbosity",
        verbosity,
    ]

    subprocess.run(cmd)


def makemigrations():
    cmd = ["python", "manage.py", "makemigrations"]
    subprocess.run(cmd)


def migrate():
    cmd = ["python", "manage.py", "migrate"]
    subprocess.run(cmd)


def test():
    cmd = ["python", "manage.py", "test"]
    subprocess.run(cmd)
