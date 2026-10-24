import logging
import os
import time

import requests
from prometheus_client import Counter, Gauge, Histogram, start_http_server

BASE_URL = os.getenv("BASE_URL", "http://frontend.boutique.svc.cluster.local")
INTERVAL = int(os.getenv("INTERVAL_SECONDS", "30"))
PORT = int(os.getenv("METRICS_PORT", "8000"))
PRODUCT_ID = "OLJCESPC7Z"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("journey-exporter")

STEP_DURATION = Histogram(
    "journey_step_duration_seconds",
    "Время выполнения шага пользовательского сценария",
    ["step"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
STEP_FAILURES = Counter(
    "journey_step_failures_total", "Число неудачных шагов", ["step"]
)
RUNS = Counter("journey_runs_total", "Число прогонов сценария", ["result"])
LAST_SUCCESS = Gauge(
    "journey_last_success_timestamp_seconds",
    "Время последнего полностью успешного прогона",
)


def do_step(session, name, method, path, **kwargs):
    """Выполняет один шаг, меряет время, считает ошибки."""
    started = time.perf_counter()
    try:
        response = session.request(method, BASE_URL + path, timeout=5, **kwargs)
        response.raise_for_status()
        return response
    except Exception: 
        STEP_FAILURES.labels(step=name).inc()
        raise
    finally:
        STEP_DURATION.labels(step=name).observe(time.perf_counter() - started)


def run_journey():
    session = requests.Session()  # хранит cookie между шагами
    do_step(session, "home", "GET", "/")
    do_step(session, "product", "GET", f"/product/{PRODUCT_ID}")
    do_step(
        session, "add_to_cart", "POST", "/cart",
        data={"product_id": PRODUCT_ID, "quantity": 1},
    )
    do_step(
        session, "checkout", "POST", "/cart/checkout",
        data={
            "email": "test@example.com",
            "street_address": "Nevsky 1",
            "zip_code": "190000",
            "city": "Saint Petersburg",
            "state": "SPB",
            "country": "Russia",
            "credit_card_number": "4432801561520454",
            "credit_card_expiration_month": "1",
            "credit_card_expiration_year": "2030",
            "credit_card_cvv": "672",
        },
    )


def main():
    start_http_server(PORT)
    log.info("Экспортер запущен, метрики на порту %s, цель %s", PORT, BASE_URL)
    while True:
        try:
            run_journey()
            RUNS.labels(result="success").inc()
            LAST_SUCCESS.set_to_current_time()
            log.info("Сценарий прошёл успешно")
        except Exception as exc: # noqa: BLE001
            RUNS.labels(result="failure").inc()
            log.error("Сценарий упал: %s", exc)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()