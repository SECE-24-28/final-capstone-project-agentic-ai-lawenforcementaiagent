import requests
import time
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

ECOURTS_URL   = os.getenv("ECOURTS_API_URL")
PHOENIX_URL   = os.getenv("PHOENIX_API_URL")
VAKEEL360_URL = os.getenv("VAKEEL360_API_URL")

RETRY_COUNT = 3
RETRY_DELAY = 30  # seconds


class APIDownException(Exception):
    pass


def _get(url, params, api_name):
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.warning(f"{api_name} attempt {attempt} failed: {e}")
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)
    raise APIDownException(f"{api_name} failed after {RETRY_COUNT} retries")


def call_ecourts_api(case_number):
    return _get(f"{ECOURTS_URL}/case-status", {"cnr": case_number}, "eCourts")


def call_phoenix_api(case_number):
    return _get(f"{PHOENIX_URL}/case", {"cnr": case_number}, "Phoenix")


def call_vakeel360_api(case_number):
    return _get(f"{VAKEEL360_URL}/case", {"cnr": case_number}, "Vakeel360")


def fetch_case(case_number, court_type="district"):
    """
    Try primary → Phoenix fallback → Vakeel360 fallback.
    Returns (data, api_used) or raises APIDownException.
    """
    try:
        return call_ecourts_api(case_number), "ecourts"
    except APIDownException:
        logger.warning(f"eCourts down for {case_number}, trying Phoenix")

    try:
        return call_phoenix_api(case_number), "phoenix"
    except APIDownException:
        logger.warning(f"Phoenix down for {case_number}, trying Vakeel360")

    if court_type in ("highcourt", "tribunal"):
        try:
            return call_vakeel360_api(case_number), "vakeel360"
        except APIDownException:
            logger.warning(f"Vakeel360 down for {case_number}")

    raise APIDownException(f"All APIs down for case {case_number}")
