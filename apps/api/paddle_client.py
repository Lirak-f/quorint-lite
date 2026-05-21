"""Shared Paddle billing client — import `paddle` from here everywhere."""

import os
from paddle_billing import Client

paddle = Client(os.getenv("PADDLE_API_KEY", ""))
