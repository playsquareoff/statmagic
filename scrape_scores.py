import urllib3
import argparse

# Suppress urllib3 warnings (urllib3 v2 has NotOpenSSLWarning, v1 doesn't)
try:
    urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)
except AttributeError:
    # urllib3 < 2.0 doesn't have NotOpenSSLWarning, so no action needed
    pass

# Also disable all urllib3 warnings as a catch-all
urllib3.disable_warnings()

import requests
from bs4 import BeautifulSoup
import json
import re

def _period_label(index: int) -> str:
    """Return the label for a given period index (supports overtime)."""
    base_labels = ['1st', '2nd', '3rd', '4th']
    if index < len(base_labels):
        return base_labels[index]
    ot_number = index - len(base_labels) + 1
    return 'OT' if ot_number == 1 else f'OT{ot_number}'


def _build_period_scores(period_values):
    """Create a period score mapping and compute the calculated final."""
    period_scores = {}
    total_points = 0
    for idx, raw_value in enumerate(period_values):
        label = _period_label(idx)
        value_str = str(raw_value)
        period_scores[label] = value_str
        try:
            total_points += int(value_str)
        except (TypeError, ValueError):
            # Skip non-numeric entries
            continue
    return period_scores, str(total_points)


def _ordered_period_keys(scores_dict):
    """Return period keys in display order (quarters followed by overtime)."""
    base_order = [label for label in ['1st', '2nd', '3rd', '4th'] if label in scores_dict]
    ot_keys = [key for key in scores_dict.keys() if key.startswith('OT')]

    def _ot_sort_key(label: str) -> int:
        if label == 'OT':
            return 1
        suffix = label[2:]
        return int(suffix) if suffix.isdigit() else 99

    ot_ordered = sorted(ot_keys, key=_ot_sort_key)
    return base_order + ot_ordered


def scrape_espn_game_scores(url):
    """
    Scrape quarter-by-quarter scores and final totals from an ESPN NFL game page.
    
    Args:
        url (str): The ESPN game URL
        
    Returns:
        dict: Dictionary containing team names, quarter scores, and final totals
    """
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
    
    # Extract data from script tags - ESPN embeds game data in JavaScript
    script_tags = soup.find_all('script')
    
    teams_data = {}
    
    for script in script_tags:
        if not script.string:
            continue
            
        content = script.string
        
        # Find all competitors with their data
        # ESPN structure: competitors array with objects containing team info, scores, linescores
        # Look for the competitor objects pattern
        competitor_pattern = r'\{[^}]*\"team\"[^}]*\"displayName\"\s*:\s*\"([^\"]+)\"[^}]*?\"score\"\s*:\s*\"(\d+)\"[^}]*?\"linescores\"\s*:\s*(\[[^\]]+\])[^}]*\}'
        
        # More flexible pattern - find displayName, score, and linescores in proximity
        # First, find all linescores arrays
        linescores_matches = list(re.finditer(r'\"linescores\"\s*:\s*(\[[^\]]+\])', content))
        
        if linescores_matches:
            # For each linescores, look backwards and forwards for team name and score
            for match in linescores_matches:
                start_pos = max(0, match.start() - 1000)  # Look 1000 chars before
                end_pos = min(len(content), match.end() + 500)  # Look 500 chars after
                context = content[start_pos:end_pos]
                
                # Extract linescores
                linescores_str = match.group(1)
                try:
                    linescores = json.loads(linescores_str)
                    period_values = []
                    for item in linescores:
                        if isinstance(item, dict):
                            period_values.append(item.get('displayValue', item.get('value', '0')))
                        else:
                            period_values.append(str(item))
                except Exception:
                    continue

                # Build ordered period scores and calculate a fallback final
                period_scores, calculated_final = _build_period_scores(period_values)

                # Find team name before this linescores
                team_match = re.search(r'"displayName"\s*:\s*"([^"]+)"', context)
                if not team_match:
                    # Try alternative patterns
                    team_match = re.search(r'"name"\s*:\s*"([^"]+)"', context)
                    if not team_match:
                        team_match = re.search(r'"abbreviation"\s*:\s*"([^"]+)"', context)

                team_name = team_match.group(1) if team_match else None

                # Find score - look for score in the same competitor object
                # Get more context around the linescores to find the correct score
                # Look for score before linescores in the same object
                obj_start = context.rfind('{', 0, match.start() - start_pos)
                obj_end = context.find('}', match.end() - start_pos)
                if obj_start >= 0 and obj_end > obj_start:
                    obj_context = context[obj_start:obj_end]
                    score_match = re.search(r'"score"\s*:\s*"?(\d+)"?', obj_context)
                    final_score = score_match.group(1) if score_match else None
                else:
                    score_match = re.search(r'"score"\s*:\s*"?(\d+)"?', context)
                    final_score = score_match.group(1) if score_match else None

                if final_score and not final_score.isdigit():
                    final_score = None

                final_value = final_score or calculated_final

                if team_name and period_scores:
                    period_scores['Final'] = final_value
                    teams_data[team_name] = period_scores
        
        # If we found teams data, we're done
        if len(teams_data) >= 2:
            break
        
        # Alternative: Look for pattern with "competitors" array
        if 'competitors' in content.lower() and len(teams_data) < 2:
            # Try to extract competitor objects more carefully
            # Find the competitors array
            comp_array_match = re.search(r'\"competitors\"\s*:\s*\[(.*?)\]', content, re.DOTALL)
            if comp_array_match:
                comp_array_str = comp_array_match.group(1)
                # Split by object boundaries (rough approximation)
                comp_objects = re.split(r'\},\s*\{', comp_array_str)
                for comp_obj in comp_objects:
                    # Extract team name
                    name_match = re.search(r'\"displayName\"\s*:\s*\"([^\"]+)\"', comp_obj)
                    # Extract score
                    score_match = re.search(r'\"score\"\s*:\s*\"?(\d+)\"?', comp_obj)
                    # Extract linescores
                    linescore_match = re.search(r'\"linescores\"\s*:\s*(\[[^\]]+\])', comp_obj)
                    
                    if name_match and linescore_match:
                        team_name = name_match.group(1)
                        linescores_str = linescore_match.group(1)
                        final_score = score_match.group(1) if score_match else None

                        try:
                            linescores = json.loads(linescores_str)
                            period_values = []
                            for item in linescores:
                                if isinstance(item, dict):
                                    period_values.append(item.get('displayValue', item.get('value', '0')))
                                else:
                                    period_values.append(str(item))

                            period_scores, calculated_final = _build_period_scores(period_values)
                            final_value = final_score if final_score else calculated_final

                            if period_scores:
                                period_scores['Final'] = final_value
                                teams_data[team_name] = period_scores
                        except Exception:
                            continue
    
    # Fallback: Extract from meta tags if we don't have complete data
    if len(teams_data) < 2:
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            content = meta.get('content', '')
            if 'final score' in content.lower():
                # Extract teams and final score from meta
                # Format: "TeamA vs TeamB NFL game, final score X-Y"
                parts = content.split('vs')
                if len(parts) == 2:
                    team1_words = parts[0].strip().split()
                    team2_words = parts[1].strip().split()
                    # Find team names (usually proper nouns)
                    team1 = team1_words[-1] if team1_words else None
                    team2 = team2_words[0] if team2_words else None
                    
                    # Extract score
                    score_match = re.search(r'(\d+)-(\d+)', parts[1])
                    if score_match and team1 and team2:
                        if team1 not in teams_data:
                            teams_data[team1] = {'Final': score_match.group(1)}
                        if team2 not in teams_data:
                            teams_data[team2] = {'Final': score_match.group(2)}
    
    if not teams_data:
        return {'error': 'Could not extract game data', 'url': url}
    
    return {'teams': teams_data}


def print_scores(game_data):
    """Pretty print the game scores"""
    print("\n" + "="*60)
    print("ESPN NFL GAME SCORES")
    print("="*60)
    
    if 'teams' in game_data:
        for team_name, scores in game_data['teams'].items():
            print(f"\n{team_name}:")
            print("-" * 40)
            period_order = _ordered_period_keys(scores)
            for period in period_order:
                label_type = 'Quarter' if period in ['1st', '2nd', '3rd', '4th'] else 'Period'
                print(f"  {period:>6} {label_type}: {scores.get(period, 'N/A')}")
            if 'Final' in scores:
                print(f"  {'Final':>6} Total: {scores['Final']}")

        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        for team_name, scores in game_data['teams'].items():
            final = scores.get('Final', 'N/A')
            period_order = _ordered_period_keys(scores)
            period_summary = ' | '.join([f"{label}: {scores.get(label, 'N/A')}" for label in period_order])
            print(f"{team_name:20} Final: {final:>3}  ({period_summary})")
    elif 'error' in game_data:
        print(f"\nError: {game_data['error']}")
    else:
        print("\nCould not extract complete game data.")
        print("Raw data:", json.dumps(game_data, indent=2))


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape quarter-by-quarter scores (including OT) from an ESPN game page."
    )
    parser.add_argument(
        "sport",
        help="Sport segment used in ESPN URLs (e.g. 'nfl', 'nba')."
    )
    parser.add_argument(
        "game_id",
        help="ESPN gameId value to scrape (e.g. '401772834')."
    )
    parser.add_argument(
        "--output",
        default="game_scores.json",
        help="Path to write the extracted scores JSON (default: game_scores.json)."
    )
    parser.add_argument(
        "--print",
        dest="should_print",
        action="store_true",
        help="Print formatted scores to stdout."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    url = f"https://www.espn.com/{args.sport}/game/_/gameId/{args.game_id}/"

    try:
        game_data = scrape_espn_game_scores(url)
        if args.should_print:
            print_scores(game_data)

        with open(args.output, 'w') as f:
            json.dump(game_data, f, indent=2)
        print(f"\n✓ Data saved to {args.output}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
