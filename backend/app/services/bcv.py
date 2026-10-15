import logging
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from bs4 import BeautifulSoup

from app.extensions import db
from app.models import ExchangeRate

logger = logging.getLogger(__name__)

DEFAULT_BCV_URL = "https://www.bcv.org.ve/"

_FALLBACK_SOURCES = (
    ("https://ve.dolarapi.com/api/v1/tasa", lambda data: str(data.get("usd", {}).get("transferencia", ""))),
    ("https://api.exchangerate.host/latest?base=USD&symbols=VES", lambda data: str(data.get("rates", {}).get("VES", ""))),
)


class BcvRateError(RuntimeError):
    pass


def _parse_decimal(value: str) -> Decimal:
    normalized = value.strip().replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise BcvRateError("The USD/VES rate could not be parsed.") from exc


def _extract_rate(text: str) -> Decimal | None:
    patterns = (
        re.compile(r"USD\s*([0-9][0-9.,]*)", re.IGNORECASE),
        re.compile(r"d[oó]lar[^s]*?([0-9]{1,3}(?:[.,][0-9]{2,3})*)", re.IGNORECASE),
        re.compile(r"([0-9]{1,3}(?:[.,][0-9]{2,3})*)\s*Bs\.?", re.IGNORECASE),
    )
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            try:
                return _parse_decimal(match.group(1))
            except BcvRateError:
                continue
    return None


def _try_fallback_source() -> tuple[Decimal, date, str]:
    for url, extractor in _FALLBACK_SOURCES:
        try:
            response = requests.get(url, timeout=10)
            if response.ok:
                raw = extractor(response.json())
                if raw:
                    return _parse_decimal(raw).quantize(Decimal("0.01")), date.today(), url
        except Exception:
            logger.warning("Fallback exchange-rate source %s failed", url, exc_info=True)
    env_rate = os.getenv("FALLBACK_BCV_RATE", "").strip()
    if env_rate:
        try:
            return _parse_decimal(env_rate).quantize(Decimal("0.01")), date.today(), "env://FALLBACK_BCV_RATE"
        except BcvRateError:
            logger.warning("FALLBACK_BCV_RATE env var could not be parsed: %s", env_rate)
    raise BcvRateError("No exchange-rate source (BCV or fallback) could provide a rate.")


def fetch_official_bcv_rate() -> tuple[Decimal, date, str]:
    source_url = os.getenv("BCV_RATE_URL", DEFAULT_BCV_URL)
    try:
        response = requests.get(source_url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (compatible; TostaduriaPlatform/1.0)"})
        response.raise_for_status()
        text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
        rate = _extract_rate(text)
        if rate and rate > 0:
            return rate.quantize(Decimal("0.01")), date.today(), source_url
        logger.warning("BCV page did not expose a USD rate; trying fallback sources.")
    except (requests.RequestException, OSError) as exc:
        logger.warning("BCV page fetch failed: %s; trying fallback sources.", exc)
    return _try_fallback_source()


def save_exchange_rate(rate_ves: Decimal, effective_date: date, source_url: str, source_method: str, note: str | None = None, user_id: int | None = None) -> ExchangeRate:
    record = db.session.scalar(
        db.select(ExchangeRate).where(ExchangeRate.currency == "USD", ExchangeRate.effective_date == effective_date)
    )
    if record is None:
        record = ExchangeRate(currency="USD", effective_date=effective_date, rate_ves=rate_ves, source_url=source_url, source_method=source_method, note=note, created_by_user_id=user_id)
        db.session.add(record)
    else:
        record.rate_ves = rate_ves
        record.source_url = source_url
        record.source_method = source_method
        record.note = note
        record.created_by_user_id = user_id
    db.session.commit()
    return record


def sync_official_bcv_rate() -> ExchangeRate:
    rate, effective_date, source_url = fetch_official_bcv_rate()
    return save_exchange_rate(rate, effective_date, source_url, "automatic")