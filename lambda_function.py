import json
import logging
import os
import base64
from typing import Any, Dict, Optional

from scrape_scores import scrape_espn_game_scores

LOGGER = logging.getLogger()
LOGGER.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def _build_response(status_code: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _extract_params(event: Dict[str, Any]) -> Dict[str, Optional[str]]:
    params = {}

    # API Gateway HTTP API / REST API
    query = event.get("queryStringParameters") or {}
    params.update({k.lower(): v for k, v in query.items() if v is not None})

    # Lambda URL (multi-value support)
    mv_query = event.get("multiValueQueryStringParameters") or {}
    for key, values in mv_query.items():
        if values:
            params[key.lower()] = values[0]

    # Direct invocation or unit tests can supply sport/gameId in the body
    body = event.get("body")
    if body:
        try:
            if event.get("isBase64Encoded"):
                body = json.loads(base64.b64decode(body))
            elif isinstance(body, str):
                body = json.loads(body)
            if isinstance(body, dict):
                for key in ("sport", "gameId", "game_id"):
                    if body.get(key) and params.get(key.lower()) is None:
                        params[key.lower()] = body[key]
        except Exception:  # body parsing best-effort
            LOGGER.debug("Unable to parse request body", exc_info=True)

    # Allow path parameters as well (e.g. /scores/{sport}/{gameId})
    path_params = event.get("pathParameters") or {}
    for key, value in path_params.items():
        if value:
            params[key.lower()] = value

    return params


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    LOGGER.debug("Received event: %s", json.dumps(event))

    params = _extract_params(event)
    sport = params.get("sport")
    game_id = params.get("gameid") or params.get("game_id")

    if not sport or not game_id:
        return _build_response(
            400,
            {
                "message": "Missing required parameters.",
                "required": {"sport": "e.g. nfl", "gameId": "e.g. 401772834"},
            },
        )

    url = f"https://www.espn.com/{sport}/game/_/gameId/{game_id}/"

    try:
        data = scrape_espn_game_scores(url)
    except Exception as exc:
        LOGGER.exception("Failed to scrape scores for %s", url)
        return _build_response(
            502,
            {
                "message": "Unable to retrieve game data from ESPN.",
                "detail": str(exc),
                "url": url,
            },
        )

    return _build_response(
        200,
        {
            "sport": sport,
            "gameId": game_id,
            "sourceUrl": url,
            "data": data,
        },
    )
