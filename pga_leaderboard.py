#!/usr/bin/env python3
"""
PGA Tour Leaderboard - via ESPN API + schedule lookup for tournament transitions.
Automatically shows current/live tournament or next scheduled one.
No hardcoded dates — schedule drives everything.
Usage: python3 pga_leaderboard.py
"""

import requests
from datetime import datetime, timedelta
import pytz
import json

EST = pytz.timezone('America/New_York')

# PGA Tour 2026 schedule — Monday of tournament week -> (name, location)
# Keep updated with actual tournament schedule
PGA_2026_SCHEDULE = {
    # JANUARY
    "2026-01-05": ("Sentry", "Kapalua, Hawaii"),
    "2026-01-12": ("Sony Open in Hawaii", "Honolulu, Hawaii"),
    "2026-01-19": ("The American Express", "La Quinta, California"),
    # FEBRUARY
    "2026-01-26": ("Farmers Insurance Open", "San Diego, CA"),
    "2026-02-02": ("WM Phoenix Open", "Scottsdale, AZ"),
    "2026-02-09": ("AT&T Pebble Beach Pro-Am", "Pebble Beach, CA"),
    "2026-02-16": ("Genesis Invitational", "Los Angeles, CA"),
    "2026-02-23": ("Cognizant Classic", "Palm Beach Gardens, FL"),
    # MARCH
    "2026-03-02": ("Arnold Palmer Invitational", "Orlando, FL"),
    "2026-03-09": ("The PLAYERS Championship", "Ponte Vedra Beach, FL"),
    "2026-03-16": ("Valspar Championship", "Palm Harbor, FL"),
    "2026-03-23": ("Texas Children's Houston Open", "Houston, TX"),
    # APRIL
    "2026-03-30": ("Valero Texas Open", "San Antonio, TX"),
    "2026-04-06": ("Masters Tournament", "Augusta, GA"),
    "2026-04-13": ("RBC Heritage", "Hilton Head, SC"),
    "2026-04-20": ("Zurich Classic of New Orleans", "New Orleans, LA"),
    "2026-04-27": ("Mexico Open", "VidantaWorld, Mexico"),
    # MAY
    "2026-05-04": ("AT&T Byron Nelson", "McKinney, TX"),
    "2026-05-11": ("PGA Championship", "Philadelphia, PA"),
    "2026-05-18": ("Charles Schwab Challenge", "Fort Worth, TX"),
    "2026-05-25": ("Memorial Tournament", "Dublin, OH"),
    # JUNE
    "2026-06-01": ("Canadian Open", "Oakville, ON"),
    "2026-06-08": ("U.S. Open", "Shinnecock Hills, NY"),
    "2026-06-15": ("Travelers Championship", "Cromwell, CT"),
    "2026-06-22": ("Rocket Classic", "Keene, NH"),
    "2026-06-29": ("John Deere Classic", "Silvis, IL"),
    # JULY
    "2026-07-06": ("Genesis Scottish Open", "North Berwick, SCO"),
    "2026-07-13": ("Open Championship", "Royal Portrush, NIR"),
    "2026-07-20": ("Barbasol Championship", "Nicholasville, KY"),
    "2026-07-27": ("3M Open", "Blaine, MN"),
    # AUGUST
    "2026-08-03": ("FedEx St. Jude Championship", "Memphis, TN"),
    "2026-08-10": ("Wyndham Championship", "Greensboro, NC"),
    "2026-08-17": ("BMW Championship", "St. Louis, MO"),
    "2026-08-24": ("Tour Championship", "Atlanta, GA"),
    # FEDEX CUP FALL
    "2026-08-31": ("Yorkshire Championship", "York, ENG"),
    "2026-09-07": ("DGF Championship", "France"),
    "2026-09-14": ("Fortinet Championship", "Napa, CA"),
    "2026-09-21": ("Black Desert Championship", "Utah"),
    "2026-09-28": ("Sanderson Farms Championship", "Jackson, MS"),
    "2026-10-05": ("Shriners Children's Open", "Las Vegas, NV"),
    "2026-10-12": ("The American Express", "La Quinta, CA"),
    "2026-10-19": ("ZOZO Championship", "Chiba, Japan"),
    "2026-10-26": ("Bermuda Championship", "Southampton, BER"),
    "2026-11-02": ("Cadillac Championship", "Doral, FL"),
    "2026-11-09": ("HSBC Champions", "Shanghai, CHN"),
    "2026-11-16": ("RSM Classic", "St. Simons Island, GA"),
    "2026-11-23": ("The Grant Thornton Invitational", "Naples, FL"),
    "2026-11-30": ("Hero World Challenge", "Nassau, BAH"),
    "2026-12-07": ("PNC Championship", "Orlando, FL"),
    "2026-12-14": ("QBE Shootout", "Naples, FL"),
}


def get_monday_of_week(date):
    """Return the Monday of the week for a given date."""
    return date - timedelta(days=date.weekday())


def get_current_tournament_from_schedule(now_est):
    """Look up current tournament from schedule based on today's date."""
    today = now_est.date()
    current_monday = get_monday_of_week(today)
    
    # Check this week and next few weeks
    for days_ahead in range(0, 5):
        check_monday = current_monday + timedelta(weeks=days_ahead)
        monday_str = check_monday.strftime('%Y-%m-%d')
        if monday_str in PGA_2026_SCHEDULE:
            name, location = PGA_2026_SCHEDULE[monday_str]
            # If it's this week, show it. If it's next week and we're Sun/Mon, show it.
            if days_ahead == 0:
                return name, location, check_monday
            elif days_ahead == 1 and today.weekday() >= 5:  # Sat or Sun
                return name, location, check_monday
    return None, None, None


def fetch_pga():
    """Fetch PGA leaderboard from ESPN API."""
    try:
        now_est = datetime.now(EST)
        day_of_week = now_est.strftime('%A')
        
        url = "https://site.api.espn.com/apis/site/v2/sports/golf/leaderboard"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        events = data.get('events', [])
        
        if not events:
            # No events — use schedule
            name, location, start_monday = get_current_tournament_from_schedule(now_est)
            if name:
                return f"⛳ {name}\n   {location} · {start_monday.strftime('%b %-d')}\n   (Schedule)"
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
        
        if isinstance(status_type, dict):
            status_id = status_type.get('id', '')
            status_detail = comp_status.get('detail', '')
        else:
            status_id = str(status_type)
            status_detail = comp_status.get('detail', '')
        
        competitors = competition.get('competitors', [])
        
        # Check if tournament is concluded
        is_concluded = status_id in ['3', '4'] or 'Final' in str(status_detail) or 'Complete' in str(status_detail)
        
        if is_concluded or day_of_week == 'Monday':
            # Tournament over or it's Monday — look up current from schedule
            sched_name, sched_loc, start_mon = get_current_tournament_from_schedule(now_est)
            if sched_name:
                prev = tournament_name if tournament_name != sched_name else "Previous"
                return f"⛳ {sched_name}\n   {sched_loc} · {start_mon.strftime('%b %-d')}\n   (Prev: {prev})"
            # Fallback: use fetch_next_tournament
            return fetch_next_tournament(tournament_name)
        
        # Tournament is active — show leaderboard
        lines = [f"⛳ {tournament_name}"]
        
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
        return f"⛳ PGA - Error: {str(e)[:80]}"


def fetch_next_tournament(previous_tournament):
    """Fallback: try to find next tournament from ESPN or web."""
    try:
        # Try ESPN schedule endpoint
        url = "https://site.api.espn.com/apis/site/v2/sports/golf/p1/scoreboard"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            events = data.get('events', [])
            for e in events:
                name = e.get('name', '')
                if name and name != previous_tournament:
                    # Try to get location from competitions
                    comp = e.get('competitions', [{}])[0]
                    venue = comp.get('venue', {}).get('fullName', '')
                    return f"⛳ {name}\n   {venue or 'TBD'}\n   (Prev: {previous_tournament})"
    except:
        pass
    
    # Last resort: use schedule
    sched_name, sched_loc, start_mon = get_current_tournament_from_schedule(datetime.now(EST))
    if sched_name:
        return f"⛳ {sched_name}\n   {sched_loc} · {start_mon.strftime('%b %-d')}\n   (Prev: {previous_tournament})"
    
    return f"⛳ PGA\n   Next tournament begins Thursday\n   (Prev: {previous_tournament})"


if __name__ == "__main__":
    print(fetch_pga())
