"""Test/runtime stream safety shim.

Ensures stdout/stderr use UTF-8 and suppresses flush errors on Windows consoles
that can surface as OSError: [Errno 22] Invalid argument during test runs.
"""

from __future__ import annotations

import sys
from io import TextIOWrapper


def _configure_stream(stream):
    """Return a stream wrapped with UTF-8 encoding and safe flush."""

    try:
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        return stream
    except Exception:
        # Fallback: wrap the underlying buffer
        buffer = getattr(stream, "buffer", None)
        if buffer is not None:
            stream = TextIOWrapper(buffer, encoding="utf-8", errors="replace")

    class _SafeStream:
        def __init__(self, inner):
            self._inner = inner

        def write(self, data):
            return self._inner.write(data)

        def flush(self):
            try:
                return self._inner.flush()
            except OSError:
                return None

        def __getattr__(self, name):
            return getattr(self._inner, name)

    return _SafeStream(stream)


sys.stdout = _configure_stream(sys.stdout)
sys.stderr = _configure_stream(sys.stderr)
# Also replace the originals in case runners use sys.__stdout__/__stderr__
sys.__stdout__ = _configure_stream(sys.__stdout__)
sys.__stderr__ = _configure_stream(sys.__stderr__)
