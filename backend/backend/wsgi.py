"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os
import threading

from django.core.wsgi import get_wsgi_application
from chord.chord import ChordNode, get_hash, get_ip_address

from asgiref.sync import async_to_sync

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

application = get_wsgi_application()


def start_chord_node():
    ip_address = get_ip_address()
    port = 4321
    node_id = get_hash(f"{ip_address}:{port}")

    node = ChordNode(ip_address, port, node_id, is_debug=False)
    async_to_sync(node.discover_join_start)()


chord_thread = threading.Thread(target=start_chord_node, daemon=True)
chord_thread.start()
