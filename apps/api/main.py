"""Quorint FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from posthog_client import init_posthog
from routers import reports, test_reports, webhooks

load_dotenv()

_sentry_dsn = os.getenv("SENTRY_DSN_API")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.05,
        environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
        release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "local"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise PostHog
    ph = init_posthog()
    app.state.posthog = ph

    # Start APScheduler retention crons
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from crons.retention import check_tariff_changes, check_new_buyers, day30_reengagement

        scheduler = AsyncIOScheduler()
        scheduler.add_job(check_tariff_changes, "cron", day_of_week="mon", hour=6, minute=0)
        scheduler.add_job(check_new_buyers, "cron", day=1, hour=7, minute=0)
        scheduler.add_job(day30_reengagement, "cron", hour=8, minute=0)
        scheduler.start()
        print("[App] APScheduler started — retention crons scheduled")
        app.state.scheduler = scheduler
    except ImportError:
        print("[App] APScheduler not installed — retention crons disabled. Run: pip install apscheduler")

    yield

    # Shutdown scheduler on app stop
    sched = getattr(app.state, "scheduler", None)
    if sched:
        sched.shutdown(wait=False)

    # Flush PostHog events before exit
    ph.flush()


app = FastAPI(
    title="Quorint API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router, prefix="/api")
app.include_router(test_reports.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
