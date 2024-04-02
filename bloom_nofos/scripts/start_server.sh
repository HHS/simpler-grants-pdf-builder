/root/.local/bin/poetry run gunicorn --workers 8 --timeout 89 --chdir bloom_nofos --bind 0.0.0.0:$PORT bloom_nofos.wsgi:application
