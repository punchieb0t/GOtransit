#!/usr/bin/env python3
"""
PGA Tour Leaderboard - via ESPN API + Tavily for next tournament
Handles tournament transitions (Thu-Sun) and shows next tournament on Mondays
Usage: python3 pga_leaderboard.py
"""

import requests
from datetime import datetime
import pytz
import urllib.request
import json
import re

EST = pytz.timezone('America/New_York')

def tavily_search(query, max_results=3):
    """Use Tavily API for web search"""
    api_key = "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"
    try:
        data = json.dumps({
            "query": query,
            "max_results": max_results
        }).encode()
        
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read())
    except Exception as e:
        return {"error": str(e)}

def fetch_pga():
    """Fetch PGA leaderboard from ESPN API"""
    try:
        now_est = datetime.now(EST)
        day_of_week = now_est.strftime('%A')
        
        url = "https://site.api.espn.com/apis/site/v2/sports/golf/leaderboard"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        events = data.get('events', [])
        
        if not events:
            return "⛳ PGA\n   No tournament data available"
        
        # Get the first (current) tournament
        event = events[0]
        tournament_name = event.get('name', 'Unknown Tournament')
        
        comps = event.get('competitions', [])
        if not comps:
            return "⛳ PGA\n   No competition data available"
        
        competition = comps[0]
        comp_status = competition.get('status', {})
        status_type = comp_status.get('type', {})
        
        # Check if status_type is a dict or string
        if isinstance(status_type, dict):
            status_id = status_type.get('id', '')
            status_detail = comp_status.get('detail', '')
            status_desc = status_type.get('description', '')
        else:
            status_id = str(status_type)
            status_detail = comp_status.get('detail', '')
            status_desc = ''
        
        competitors = competition.get('competitors', [])
        
        # Determine what to show
        # If it's Monday or the tournament is over (Final/Complete), show next tournament info
        is_concluded = status_id in ['3', '4'] or 'Final' in str(status_detail) or 'Complete' in str(status_detail)
        
        if day_of_week == 'Monday' or is_concluded:
            # On Monday or after tournament ends, fetch next tournament info via search
            # But first check if ESPN still shows stale data (e.g., Masters from last week)
            if is_concluded and tournament_name == 'Masters Tournament':
                # Masters ended Wed Apr 9 — RBC Heritage is Apr 13-19
                # Zurich Classic is Apr 20-26
                today = now_est.date()
                if today >= datetime(2026, 4, 13).date():
                    return "⛳ RBC Heritage\n   Hilton Head, SC · Apr 13-19\n   (Prev: Masters Tournament)"
            return fetch_next_tournament(tournament_name)
        
        # Tournament is active - show leaderboard
        lines = [f"⛳ {tournament_name}"]
        
        # Add status if available
        if status_detail:
            lines[0] += f" ({status_detail})"
        
        if competitors:
            sorted_comp = []
            for c in competitors:
                athlete = c.get('athlete', {})
                name = athlete.get('displayName', 'Unknown')
                score = c.get('score', {})
                display = score.get('displayValue', '0') if score else '0'
                
                try:
                    if display == 'E':
                        sort_val = 0
                    elif display.startswith('+'):
                        sort_val = int(display[1:])
                    elif display.startswith('-'):
                        sort_val = int(display)
                    else:
                        sort_val = int(display)
                except:
                    sort_val = 999
                
                sorted_comp.append({'name': name, 'score': display, 'sort': sort_val})
            
            sorted_comp.sort(key=lambda x: x['sort'])
            
            for entry in sorted_comp[:12]:
                lines.append(f"{entry['score']} {entry['name']}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"⛳ PGA - Error: {str(e)[:50]}"

def fetch_next_tournament(previous_tournament):
    """Fetch info about the next upcoming tournament using Tavily"""
    try:
        # Search for the next tournament
        current_month = datetime.now(EST).strftime('%B %Y')
        result = tavily_search(f"PGA Tour this week {current_month} next tournament schedule", max_results=5)
        
        if 'results' in result:
            text = json.dumps(result)
            
            # Full 2026 PGA Tour schedule (majors first, then chronologically)
            upcoming = {
                # MAJORS
                'Masters': 'Masters Tournament',
                'PGA Championship': 'PGA Championship',
                'U.S. Open': 'U.S. Open',
                'Open Championship': 'The Open Championship',
                # SIGNATURE EVENTS
                'AT&T Pebble Beach': 'AT&T Pebble Beach Pro-Am',
                'Genesis Invitational': 'Genesis Invitational',
                'Arnold Palmer': 'Arnold Palmer Invitational',
                'The Players': 'The Players Championship',
                'RBC Heritage': 'RBC Heritage',
                'Cadillac Championship': 'Cadillac Championship',
                'Truist Championship': 'Truist Championship',
                'Memorial': 'Memorial Tournament',
                'Travelers Championship': 'Travelers Championship',
                'Genesis Scottish Open': 'Genesis Scottish Open',
                'FedEx St. Jude': 'FedEx St. Jude Championship',
                'BMW Championship': 'BMW Championship',
                # REGULAR EVENTS
                'Sony Open': 'Sony Open in Hawaii',
                'American Express': 'The American Express',
                'Farmers Insurance': 'Farmers Insurance Open',
                'WM Phoenix': 'WM Phoenix Open',
                'Cognizant Classic': 'Cognizant Classic',
                'Puerto Rico Open': 'Puerto Rico Open',
                'Valspar': 'Valspar Championship',
                'Houston Open': "Texas Children's Houston Open",
                'Valero Texas Open': 'Valero Texas Open',
                'Zurich Classic': 'Zurich Classic of New Orleans',
                'Myrtle Beach': 'Oneflight Myrtle Beach Classic',
                'CJ Cup': 'CJ Cup Byron Nelson',
                'Charles Schwab': 'Charles Schwab Challenge',
                'RBC Canadian': 'RBC Canadian Open',
                'John Deere': 'John Deere Classic',
                'ISCO Championship': 'ISCO Championship',
                'Corales Puntacana': 'Corales Puntacana Championship',
                '3M Open': '3M Open',
                'Rocket Classic': 'Rocket Classic',
                'Wyndham Championship': 'Wyndham Championship',
                'Tour Championship': 'Tour Championship',
                # FEDEX CUP FALL
                'Biltmore': 'Biltmore Championship',
                'Bank of Utah': 'Bank of Utah Championship',
                'Baycurrent': 'Baycurrent Classic',
                'Butterfield Bermuda': 'Butterfield Bermuda Championship',
                'VidantaWorld': 'VidantaWorld Mexico Open',
                'World Wide Technology': 'World Wide Technology Championship',
                'Good Good': 'Good Good Championship',
                'RSM Classic': 'RSM Classic',
            }
            
            text_lower = text.lower()
            for key, full_name in upcoming.items():
                if key.lower() in text_lower:
                    return f"⛳ {full_name}\n   Starts Thursday\n   (Prev: {previous_tournament} Final)"
            
            # Try to extract tournament name from snippets
            patterns = [
                r'([A-Z][a-zA-Z]+(?:\\s+[A-Z][a-zA-Z]+){0,3}\\s+(?:Invitational|Classic|Open|Championship))',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    tournament = matches[0].strip()
                    if 5 < len(tournament) < 50:
                        return f"⛳ {tournament}\n   Starts Thursday\n   (Prev: {previous_tournament} Final)"
        
        # Fallback
        return f"⛳ PGA\n   Next tournament begins Thursday\n   (Prev: {previous_tournament} Final)"
        
    except Exception as e:
        return f"⛳ PGA\n   Next tournament begins Thursday\n   (Prev: {previous_tournament} Final)"

if __name__ == "__main__":
    print(fetch_pga())
