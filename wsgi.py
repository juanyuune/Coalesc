"""WSGI entry point, e.g. ``gunicorn wsgi:app``."""
from coalesc import create_app

app = create_app()
