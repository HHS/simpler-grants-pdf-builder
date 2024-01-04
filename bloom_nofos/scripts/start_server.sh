/root/.local/bin/poetry run gunicorn --workers 8 --chdir bloom_nofos --bind 0.0.0.0:$PORT bloom_nofos.wsgi:application
