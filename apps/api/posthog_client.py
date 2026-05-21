"""PostHog analytics client — singleton used across the application."""

import atexit
import os

from posthog import Posthog

posthog_client: Posthog | None = None


def init_posthog() -> Posthog:
    """Initialise the PostHog client and register shutdown hook."""
    global posthog_client
    api_key = os.getenv("POSTHOG_API_KEY", "")
    host = os.getenv("POSTHOG_HOST")

    kwargs = {"enable_exception_autocapture": True}
    if host:
        kwargs["host"] = host

    posthog_client = Posthog(api_key, **kwargs)
    atexit.register(posthog_client.shutdown)
    return posthog_client


def get_posthog() -> Posthog | None:
    return posthog_client
