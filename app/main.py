"""RealtyDog entrypoint: FastAPI + in-process APScheduler.

Jobs are registered as skeletons here; each maps to a section of the build
spec (README). Fill them in per the roadmap — Week 1 starts with tax-sale
lists (Job 1) and the CAD universe (Job 2).
"""
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from app.config import settings
from app.db import db_ok

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("realtydog")

scheduler = AsyncIOScheduler(timezone="America/Chicago")


# --- Scheduled jobs (skeletons — see README §§5, 9) -------------------------
async def job_tax_sale_lists() -> None:
    log.info("job_tax_sale_lists (Job 1): not implemented yet")


async def job_foreclosure_postings() -> None:
    log.info("job_foreclosure_postings (Job 3): not implemented yet")


async def job_probate_lis_pendens() -> None:
    log.info("job_probate_lis_pendens (Job 4): not implemented yet")


async def job_craigslist_rss() -> None:
    log.info("job_craigslist_rss (Job 7): not implemented yet")


async def job_cad_refresh() -> None:
    log.info("job_cad_refresh (Job 2): not implemented yet")


async def job_nonprofit_990() -> None:
    log.info("job_nonprofit_990 (Job 8): not implemented yet")


async def job_nightly_score_and_digest() -> None:
    log.info("job_nightly_score_and_digest: not implemented yet")


def register_jobs() -> None:
    scheduler.add_job(job_tax_sale_lists, CronTrigger(day_of_week="mon", hour=6), id="tax_sale_lists")
    scheduler.add_job(job_foreclosure_postings, CronTrigger(day_of_week="mon", hour=7), id="foreclosure")
    scheduler.add_job(job_probate_lis_pendens, CronTrigger(day_of_week="mon", hour=7, minute=30), id="probate")
    scheduler.add_job(job_craigslist_rss, CronTrigger(hour="*/6"), id="craigslist_rss")
    scheduler.add_job(job_cad_refresh, CronTrigger(day=1, hour=5), id="cad_refresh")
    scheduler.add_job(job_nonprofit_990, CronTrigger(day=2, hour=5), id="nonprofit_990")
    scheduler.add_job(job_nightly_score_and_digest, CronTrigger(hour=3), id="nightly_digest")


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_jobs()
    scheduler.start()
    log.info("RealtyDog started (env=%s) — %d jobs registered", settings.environment, len(scheduler.get_jobs()))
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="RealtyDog", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "realtydog",
        "env": settings.environment,
        "db": db_ok(),
        "jobs": len(scheduler.get_jobs()),
    }
