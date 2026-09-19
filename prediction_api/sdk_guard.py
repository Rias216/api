"""Audit-only guard for the tested SDK versions; not a general sandbox."""
from contextlib import contextmanager
from unittest.mock import patch
import httpx


@contextmanager
def sdk_reads_only():
    original = httpx.Client.send
    def guarded(self, request, *args, **kwargs):
        if request.method != 'GET' or '/update' in request.url.path:
            raise RuntimeError('SDK read-only guard blocked a non-read request')
        return original(self, request, *args, **kwargs)
    with patch.object(httpx.Client, 'send', guarded):
        yield
