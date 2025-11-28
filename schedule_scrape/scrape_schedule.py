import urllib3
import argparse
import logging
import os
import base64
from typing import Any, Dict, Optional

# Suppress urllib3 warnings
try:
    urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)
except AttributeError:
    pass
urllib3.disable_warnings()

import requests
from bs4 import BeautifulSoup
import json
import re

LOGGER = logging.getLogger()
LOGGER.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def scrape_espn_schedule(url, team_name_long=None):
    """
    Scrape upcoming games from an ESPN NFL team schedule page.
    
    Args:
        url (str): The ESPN team schedule URL
        team_name_long (str): The team name long format (e.g., "minnesota-vikings") for extracting team name
        
    Returns:
        list: List of dictionaries containing game information (WK, DATE, MATCH_UP, TIME, TV, GAME_ID)
    """
    # Extract team name from team_name_long (e.g., "minnesota-vikings" -> "Minnesota")
    team_name = "Minnesota"  # Default
    if team_name_long:
        # Extract the first part before hyphen and capitalize
        team_name = team_name_long.split('-')[0].capitalize()
    else:
        # Fallback: try to extract from URL if team_name_long not provided
        team_match = re.search(r'/name/[^/]+/([^/]+)', url)
        if team_match:
            team_slug = team_match.group(1)
            team_name = team_slug.split('-')[0].capitalize()
    # Fetch the webpage
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch the webpage: {e}")
    
    # Parse the HTML
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the table that contains upcoming games (has TIME column, not RESULT column)
    # Look for all tables and find the one with TIME in header but not RESULT
    tables = soup.find_all('table')
    
    target_table = None
    header_row = None
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            headers_in_row = row.find_all(['th', 'td'])
            header_texts = [h.get_text(strip=True).upper() for h in headers_in_row]
            # Look for table with TIME but NOT RESULT in header
            has_time = any('TIME' in text for text in header_texts)
            has_result = any('RESULT' in text for text in header_texts)
            if has_time and not has_result:
                target_table = table
                header_row = row
                break
        if target_table:
            break
    
    if not target_table or not header_row:
        raise Exception("Could not find schedule table with TIME column (upcoming games)")
    
    # Find all rows in the target table
    rows = target_table.find_all('tr')
    
    # Get column indices
    header_cells = header_row.find_all(['th', 'td'])
    column_indices = {}
    for idx, cell in enumerate(header_cells):
        text = cell.get_text(strip=True).upper()
        if 'WK' in text or 'WEEK' in text:
            column_indices['wk'] = idx
        elif 'DATE' in text:
            column_indices['date'] = idx
        elif 'OPPONENT' in text or 'OPP' in text:
            column_indices['opponent'] = idx
        elif 'TIME' in text:
            column_indices['time'] = idx
        elif 'TV' in text:
            column_indices['tv'] = idx
        elif 'RESULT' in text:
            column_indices['result'] = idx
    
    games = []
    
    # Process data rows
    for row in rows:
        # Skip header row
        if row == header_row:
            continue
        
        cells = row.find_all('td')
        if len(cells) < max(column_indices.values()) + 1:
            continue
        
        # Skip rows that don't have a time column (these are likely header rows or invalid)
        if 'time' not in column_indices:
            continue
        
        # Skip header rows that have column names as values
        wk_value = cells[column_indices.get('wk', 0)].get_text(strip=True).upper() if 'wk' in column_indices else ''
        if wk_value == 'WK' or wk_value == 'WEEK':
            continue
        
        # Check if the time cell contains "W" or "L" - these are played games that shouldn't be here
        # but let's be safe and skip them
        time_cell = cells[column_indices['time']]
        time_text = time_cell.get_text(strip=True).upper()
        if time_text in ['W', 'L', 'T'] or time_text.startswith('W') or time_text.startswith('L') or time_text.startswith('T'):
            if time_text not in ['TBD']:
                print(f"Skipping game with time text: {time_text}")
                continue
        
        # Extract game data
        game = {}
        
        # Extract WK
        if 'wk' in column_indices:
            wk_cell = cells[column_indices['wk']]
            game['WK'] = wk_cell.get_text(strip=True)
        
        # Extract DATE
        if 'date' in column_indices:
            date_cell = cells[column_indices['date']]
            game['DATE'] = date_cell.get_text(strip=True)
        
        # Extract OPPONENT and create MATCH_UP with team name
        if 'opponent' in column_indices:
            opponent_cell = cells[column_indices['opponent']]
            opponent_text = opponent_cell.get_text(strip=True)
            # Format opponent text: add space after @ or vs, and capitalize vs to VS
            if opponent_text.startswith('@'):
                opponent_text = f"@ {opponent_text[1:]}"
            elif opponent_text.startswith('vs'):
                opponent_text = f"VS {opponent_text[2:]}"
            # Add team name to create match-up (e.g., "Minnesota @ Seattle" or "Minnesota VS Washington")
            game['MATCH_UP'] = f"{team_name} {opponent_text}"
        
        # Extract TIME and GAME_ID from the time column
        if 'time' in column_indices:
            time_cell = cells[column_indices['time']]
            # Get the time text
            time_span = time_cell.find('span')
            if time_span:
                time_text = time_span.get_text(strip=True)
            else:
                time_text = time_cell.get_text(strip=True)
            # Add EST to the time (unless it's TBD)
            if time_text.upper() != 'TBD':
                game['TIME'] = f"{time_text} EST"
            else:
                game['TIME'] = time_text
            
            # Extract GAME_ID from href in the time column
            link = time_cell.find('a', href=True)
            if link:
                href = link.get('href')
                # Extract gameId from URL like: /nfl/game/_/gameId/401772896/vikings-seahawks
                game_id_match = re.search(r'/gameId/(\d+)', href)
                if game_id_match:
                    game['GAME_ID'] = game_id_match.group(1)
        
        # Extract TV
        if 'tv' in column_indices:
            tv_cell = cells[column_indices['tv']]
            game['TV'] = tv_cell.get_text(strip=True)
        
        # Only add games that have at least some data
        if game:
            games.append(game)
    
    return games


def _build_response(status_code: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build a Lambda response with proper status code and headers."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _extract_params(event: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Extract parameters from Lambda event (query params, body, or path params)."""
    params = {}

    # API Gateway HTTP API / REST API
    query = event.get("queryStringParameters") or {}
    params.update({k.lower(): v for k, v in query.items() if v is not None})

    # Lambda URL (multi-value support)
    mv_query = event.get("multiValueQueryStringParameters") or {}
    for key, values in mv_query.items():
        if values:
            params[key.lower()] = values[0]

    # Direct invocation or unit tests can supply parameters in the body
    body = event.get("body")
    if body:
        try:
            if event.get("isBase64Encoded"):
                body = json.loads(base64.b64decode(body))
            elif isinstance(body, str):
                body = json.loads(body)
            if isinstance(body, dict):
                for key in ("team_slug", "teamSlug", "team_name_long", "teamNameLong"):
                    if body.get(key):
                        # Normalize key names
                        normalized_key = key.lower().replace("slug", "_slug").replace("namelong", "_name_long")
                        if params.get(normalized_key) is None:
                            params[normalized_key] = body[key]
        except Exception:  # body parsing best-effort
            LOGGER.debug("Unable to parse request body", exc_info=True)

    # Allow path parameters as well (e.g. /schedule/{team_slug}/{team_name_long})
    path_params = event.get("pathParameters") or {}
    for key, value in path_params.items():
        if value:
            params[key.lower()] = value

    return params


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function for scraping ESPN NFL team schedules.
    
    Accepts parameters via:
    - Query string: ?team_slug=min&team_name_long=minnesota-vikings
    - Request body: {"team_slug": "min", "team_name_long": "minnesota-vikings"}
    - Path parameters: /schedule/{team_slug}/{team_name_long}
    
    Returns:
        Dict with statusCode, headers, and body containing the schedule data
    """
    LOGGER.debug("Received event: %s", json.dumps(event))

    params = _extract_params(event)
    team_slug = params.get("team_slug")
    team_name_long = params.get("team_name_long")

    # Default values if not provided
    if not team_slug:
        team_slug = "min"
    if not team_name_long:
        team_name_long = "minnesota-vikings"

    # Build URL dynamically from team_slug and team_name_long
    url = f"https://www.espn.com/nfl/team/schedule/_/name/{team_slug}/{team_name_long}"

    try:
        games = scrape_espn_schedule(url, team_name_long)
    except Exception as exc:
        LOGGER.exception("Failed to scrape schedule for %s", url)
        return _build_response(
            502,
            {
                "message": "Unable to retrieve schedule data from ESPN.",
                "detail": str(exc),
                "url": url,
                "team_slug": team_slug,
                "team_name_long": team_name_long,
            },
        )

    return _build_response(
        200,
        {
            "team_slug": team_slug,
            "team_name_long": team_name_long,
            "sourceUrl": url,
            "games": games,
            "count": len(games),
        },
    )


def _create_lambda_event_from_flask_request(request) -> Dict[str, Any]:
    """Convert Flask request to Lambda event format."""
    event = {
        "httpMethod": request.method,
        "path": request.path,
        "queryStringParameters": dict(request.args) if request.args else None,
        "multiValueQueryStringParameters": {k: request.args.getlist(k) for k in request.args} if request.args else None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
    }
    
    # Extract path parameters if using route like /schedule/<team_slug>/<team_name_long>
    if request.view_args:
        event["pathParameters"] = request.view_args
    
    # Handle request body
    if request.is_json:
        event["body"] = json.dumps(request.get_json())
    elif request.data:
        try:
            event["body"] = request.data.decode('utf-8')
        except:
            event["body"] = None
    
    return event


def _run_local_server(host="127.0.0.1", port=5000):
    """Run a local Flask server that wraps the Lambda handler."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("Error: Flask is required to run the local server.")
        print("Install it with: pip install flask")
        return
    
    app = Flask(__name__)
    
    @app.route("/", methods=["GET", "POST"])
    @app.route("/schedule", methods=["GET", "POST"])
    def schedule_handler():
        """Handle schedule requests."""
        try:
            # Convert Flask request to Lambda event
            event = _create_lambda_event_from_flask_request(request)
            
            # Call Lambda handler
            response = lambda_handler(event, None)
            
            # Parse Lambda response and return Flask response
            status_code = response["statusCode"]
            body = json.loads(response["body"])
            
            return jsonify(body), status_code
        except Exception as e:
            LOGGER.exception("Error handling request")
            return jsonify({"message": "Internal server error", "detail": str(e)}), 500
    
    @app.route("/schedule/<team_slug>/<team_name_long>", methods=["GET", "POST"])
    def schedule_with_path(team_slug, team_name_long):
        """Handle schedule requests with path parameters."""
        try:
            # Convert Flask request to Lambda event
            event = _create_lambda_event_from_flask_request(request)
            # Add path parameters
            event["pathParameters"] = {
                "team_slug": team_slug,
                "team_name_long": team_name_long
            }
            
            # Call Lambda handler
            response = lambda_handler(event, None)
            
            # Parse Lambda response and return Flask response
            status_code = response["statusCode"]
            body = json.loads(response["body"])
            
            return jsonify(body), status_code
        except Exception as e:
            LOGGER.exception("Error handling request")
            return jsonify({"message": "Internal server error", "detail": str(e)}), 500
    
    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        return jsonify({"status": "healthy"}), 200
    
    print(f"\n{'='*80}")
    print("Local Schedule Scraper Server")
    print(f"{'='*80}")
    print(f"Server running at: http://{host}:{port}")
    print(f"\nEndpoints:")
    print(f"  GET/POST http://{host}:{port}/schedule?team_slug=min&team_name_long=minnesota-vikings")
    print(f"  GET/POST http://{host}:{port}/schedule/<team_slug>/<team_name_long>")
    print(f"  GET      http://{host}:{port}/health")
    print(f"\nExample:")
    print(f"  curl 'http://{host}:{port}/schedule?team_slug=dal&team_name_long=dallas-cowboys'")
    print(f"{'='*80}\n")
    
    app.run(host=host, port=port, debug=False)


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape upcoming games from an ESPN NFL team schedule page."
    )
    parser.add_argument(
        "--team-slug",
        dest="team_slug",
        default="min",
        help="Team slug for URL (e.g., 'min' for Minnesota Vikings). Default: min"
    )
    parser.add_argument(
        "--team-name-long",
        dest="team_name_long",
        default="minnesota-vikings",
        help="Team name long format for URL (e.g., 'minnesota-vikings'). Default: minnesota-vikings"
    )
    parser.add_argument(
        "--output",
        default="schedule.json",
        help="Path to write the extracted schedule JSON (default: schedule.json)."
    )
    parser.add_argument(
        "--print",
        dest="should_print",
        action="store_true",
        help="Print formatted schedule to stdout."
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run as a local HTTP server instead of scraping once."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind the server to (default: 5000)."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    
    # If --server flag is set, run as local server
    if args.server:
        _run_local_server(host=args.host, port=args.port)
    else:
        # Original command-line scraping functionality
        # Build URL dynamically from team_slug and team_name_long
        url = f"https://www.espn.com/nfl/team/schedule/_/name/{args.team_slug}/{args.team_name_long}"

        print(f"\nURL: {url}\n")
        
        try:
            games = scrape_espn_schedule(url, args.team_name_long)
            
            if args.should_print:
                print("\n" + "="*80)
                print("ESPN NFL SCHEDULE - UPCOMING GAMES")
                print("="*80)
                for game in games:
                    print(f"\nWeek {game.get('WK', 'N/A')}")
                    print(f"  Date: {game.get('DATE', 'N/A')}")
                    print(f"  Match-up: {game.get('MATCH_UP', 'N/A')}")
                    print(f"  Time: {game.get('TIME', 'N/A')}")
                    print(f"  TV: {game.get('TV', 'N/A')}")
                    print(f"  Game ID: {game.get('GAME_ID', 'N/A')}")
            
            with open(args.output, 'w') as f:
                json.dump(games, f, indent=2)
            print(f"\n✓ Data saved to {args.output}")
            print(f"✓ Found {len(games)} upcoming game(s)")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

