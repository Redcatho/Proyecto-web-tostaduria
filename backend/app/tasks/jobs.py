from datetime import UTC, datetime


def health_probe() -> dict[str, str]:
    """Small task used to verify Redis and the worker without business side effects."""
    return {"status": "ok", "processed_at": datetime.now(UTC).isoformat()}


def sync_bcv_rate_job() -> dict[str, str]:
    from app import create_app
    from app.services.bcv import sync_official_bcv_rate

    app = create_app()
    with app.app_context():
        rate = sync_official_bcv_rate()
        return {"status": "ok", "rate_ves": str(rate.rate_ves), "effective_date": rate.effective_date.isoformat()}
