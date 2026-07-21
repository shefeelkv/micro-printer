"""
WSGI config for micro_copy_maker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'micro_copy_maker.settings')

application = get_wsgi_application()

# Run migrations automatically on Vercel
if 'VERCEL' in os.environ:
    try:
        call_command('migrate', interactive=False)
    except Exception as e:
        print(f"Error running migrations on Vercel startup: {e}")

app = application


