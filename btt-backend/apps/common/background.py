"""
apps/common/background.py
Fire-and-forget dispatch for notification and email side effects.

Every such side effect follows the same contract: it runs off the request
thread, and a failure to deliver must never fail the request that triggered it.
`background_task` encodes the swallow-and-log half, `run_in_background` the
dispatch half. `deferred_task` combines the two into the shape the view modules
actually need — a lazily-resolved call into the notification or email service.

Note for tests: `threading.Thread` is looked up on the module at call time, so
the synchronous-thread fixture in tests/conftest.py continues to apply.
"""
import functools
import importlib
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


def deferred_task(module_path, attr, error_message):
    """
    Build a background side effect that calls `module_path.attr` lazily.

    The views need the import deferred for two reasons: the notification and
    email services import back from the view modules, and tests patch those
    services by their canonical path. Resolving the attribute at call time
    rather than import time satisfies both — a patched attribute is picked up,
    and no import cycle forms at startup.

    Failures are logged against the *target* module's logger and swallowed, so a
    dead SMTP host can never fail the request that triggered the send.
    """
    def call(*args, **kwargs):
        return getattr(importlib.import_module(module_path), attr)(*args, **kwargs)

    call.__name__ = attr
    call.__module__ = module_path
    return background_task(error_message)(call)
