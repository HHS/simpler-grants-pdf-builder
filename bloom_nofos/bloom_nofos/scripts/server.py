import subprocess


def main():
    cmd = ["python", "manage.py", "runserver", "0.0.0.0:8000"]
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
