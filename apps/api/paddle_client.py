"""Shared Paddle billing client — import `paddle` from here everywhere."""

import os
from paddle_billing import Client, Environment, Options

_key = os.getenv("PADDLE_API_KEY", "")
_env = Environment.SANDBOX if "sdbx" in _key else Environment.PRODUCTION

paddle = Client(_key, options=Options(environment=_env))
