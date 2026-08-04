"""
apps/common/background.py
Fire-and-forget dispatch for notification and email side effects.

Every such side effect follows the same contract: it runs off the request
thread, and a failure to deliver must never fail the request that triggered it.
`background_task` encodes the swallow-and-log half, `run_in_background` the
dispatch half.

Note for tests: `threading.Thread` is looked up on the module at call time, so
the synchronous-thread fixture in tests/conftest.py continues to apply.
"""
import functools
import logging
import threading


def background_task(error_message):
    """
    Mark a callable as a background side effect: exceptions are logged against
    the defining module's logger and swallowed.

    `error_message` is a %-style format string taking the exception, e.g.
    "Failed to send theft report notification: %s".
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                logging.getLogger(func.__module__).error(error_message, exc)
        return wrapper
    return decorator


def run_in_background(target, *args, **kwargs):
    """Dispatch `target(*args, **kwargs)` on a daemon thread."""
    threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()
