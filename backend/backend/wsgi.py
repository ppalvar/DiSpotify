"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os
import socket
import asyncio
import logging

from django.core.wsgi import get_wsgi_application
from chord.chord import ChordNode, get_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

application = get_wsgi_application()


def get_ip_address() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
    except Exception:
        ip_address = "127.0.0.1"
    return ip_address


ip_address = get_ip_address()
port = 4321  # Default port for the chord algorithm, for no particular reason
node_id = get_hash(f"{ip_address}:{port}")

logger.info(f"node {node_id}")

node = ChordNode(ip_address, port, node_id, is_debug=True)
asyncio.run(node.start())
