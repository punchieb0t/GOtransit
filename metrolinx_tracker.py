#!/usr/bin/env python3
"""
Metrolinx GO Transit Departures Tracker
Uses official Metrolinx Open API
"""

import requests
import json
from datetime import datetime
import os

API_KEY = "30026843"
BASE_URL = "https://api.openmetrolinx.com/OpenDataAPI/api/V1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

STATIONS = {
    "CL": "Clarkson GO",
    "CLARKSON": "Clarkson GO",
    "PO": "Port Credit",
    "PORT": "Port Credit",
    "PORT CREDIT": "Port Credit",
    "OA": "Oakville GO",
    "OAKVILLE": "Oakville GO",
    "ML": "Milton GO",
    "MILTON": "Milton GO",
    "UN": "Union Station",
    "UNION": "Union Station",
}

def get_next_departures(stop_code, limit=5, max_retries=2):
    url = f"{BASE_URL}/Stop/NextService"
    params = {"key": API_KEY, "stopCode": stop_code}

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            data = resp.json()

            error_code = data.get("Metadata", {}).get("ErrorCode")

            if error_code == "204":
                return []

            if error_code != "200":
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1)
                    continue
                return {"error": data.get("Metadata", {}).get("ErrorMessage", f"API error: {error_code}")}

            service = data.get("NextService") or {}
            departures = service.get("Lines", [])
            return departures[:limit]
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(1)
                continue
            return {"error": str(e)}

    return {"error": "Max retries exceeded"}


def format_departures(departures, stop_name):
    if isinstance(departures, dict) and "error" in departures:
        return f"❌ Error: {departures['error']}"

    if not departures:
        return f"No departures found for {stop_name}"

    lines = [f"🚂 *{stop_name}* - Next Departures"]
    lines.append("")

    now = datetime.now()

    for dep in departures:
        direction = dep.get("DirectionName", "Unknown")
        platform = dep.get("ScheduledPlatform", "")
        time = dep.get("ScheduledDepartureTime", "")
        computed = dep.get("ComputedDepartureTime", "")
        status = dep.get("Status", "S")

        departure_time = computed if computed else time

        if departure_time:
            try:
                dep_dt = datetime.strptime(departure_time, "%Y-%m-%d %H:%M:%S")
                mins = int((dep_dt - now).total_seconds() / 60)
                time_str = f"{mins} min"
                if status == "D":
                    time_str += " (Delayed)"
                elif status == "C":
                    time_str += " (Cancelled)"
            except:
                time_str = departure_time
        else:
            time_str = "TBD"

        plat_str = f" (P{platform})" if platform else ""
        lines.append(f"  → {direction}: {time_str}{plat_str}")

    lines.append("")
    lines.append(f"_Updated: {now.strftime('%I:%M')}_")
    return "\n".join(lines)


def format_both_directions():
    """Get accurate departures for both directions on Lakeshore West - ORIGINAL FORMAT"""
    cl_url = f"{BASE_URL}/Stop/NextService"
    un_url = f"{BASE_URL}/Stop/NextService"

    cl_params = {"key": API_KEY, "stopCode": "CL"}
    un_params = {"key": API_KEY, "stopCode": "UN"}

    now = datetime.now()
    lines = ["🚂 Lakeshore West - Live Times"]
    lines.append("")

    max_retries = 3
    cl_data = {}
    un_data = {}

    for attempt in range(max_retries):
        try:
            cl_resp = requests.get(cl_url, params=cl_params, headers=HEADERS, timeout=15)
            un_resp = requests.get(un_url, params=un_params, headers=HEADERS, timeout=15)

            try:
                cl_data = cl_resp.json() if cl_resp.status_code == 200 else {"Metadata": {"ErrorCode": "000"}}
            except:
                cl_data = {"Metadata": {"ErrorCode": "000"}}
            try:
                un_data = un_resp.json() if un_resp.status_code == 200 else {"Metadata": {"ErrorCode": "000"}}
            except:
                un_data = {"Metadata": {"ErrorCode": "000"}}

            cl_error = cl_data.get("Metadata", {}).get("ErrorCode", "200")
            un_error = un_data.get("Metadata", {}).get("ErrorCode", "200")

            if cl_error == "204" or un_error == "204":
                lines.append("🌙 No GO Transit service at this time (service runs ~6 AM - midnight)")
                return "\n".join(lines)

            cl_service = cl_data.get("NextService") or {}
            un_service = un_data.get("NextService") or {}
            cl_lines = cl_service.get("Lines", [])
            un_lines = un_service.get("Lines", [])

            if not cl_lines and not un_lines:
                lines.append("🌙 No GO Transit service at this time")
                return "\n".join(lines)

            if cl_error == "200" and un_error == "200":
                break
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            lines.append(f"❌ API Error: {str(e)}")
            return "\n".join(lines)

    # Eastbound (Clarkson → Union)
    lines.append("Eastbound → Union")
    to_union = []
    for dep in cl_service.get("Lines", []):
        direction = dep.get("DirectionName", "").strip()
        if "Union" in direction:
            computed = dep.get("ComputedDepartureTime", "")
            scheduled = dep.get("ScheduledDepartureTime", "")
            platform = dep.get("ScheduledPlatform", "")
            if computed:
                dep_time = datetime.strptime(computed, "%Y-%m-%d %H:%M:%S")
                mins = int((dep_time - now).total_seconds() / 60)
                delay = 0
                if scheduled:
                    try:
                        delay = int((dep_time - datetime.strptime(scheduled, "%Y-%m-%d %H:%M:%S")).total_seconds())
                    except:
                        pass
                if mins >= 0:
                    to_union.append((mins, delay, platform))

    to_union.sort(key=lambda x: x[0])
    if to_union:
        for m, d, p in to_union[:3]:
            delay_str = f" ⏱️ (+{d//60})" if d >= 60 else ""
            plat_str = f" (P{p})" if p else ""
            lines.append(f"• {m} min{delay_str}{plat_str}")
    else:
        lines.append("• No service")

    lines.append("")
    lines.append("Westbound → Clarkson")

    from_union = []
    for dep in un_service.get("Lines", []):
        line_code = dep.get("LineCode", "")
        direction = dep.get("DirectionName", "").strip()
        if line_code == "LW" and "Union" not in direction:
            computed = dep.get("ComputedDepartureTime", "")
            scheduled = dep.get("ScheduledDepartureTime", "")
            platform = dep.get("ScheduledPlatform", "")
            if computed:
                dep_time = datetime.strptime(computed, "%Y-%m-%d %H:%M:%S")
                mins = int((dep_time - now).total_seconds() / 60)
                delay = 0
                if scheduled:
                    try:
                        delay = int((dep_time - datetime.strptime(scheduled, "%Y-%m-%d %H:%M:%S")).total_seconds())
                    except:
                        pass
                if mins >= 0:
                    dest = direction.replace("LW - ", "").replace(" GO", "").strip()
                    from_union.append((dest, mins, delay, platform))

    from_union.sort(key=lambda x: x[1])
    if from_union:
        for dest, m, d, p in from_union[:3]:
            delay_str = f" ⏱️ (+{d//60})" if d >= 60 else ""
            plat_str = f" (P{p})" if p else ""
            lines.append(f"• {m} min{delay_str}{plat_str}")
    else:
        lines.append("• No service")

    lines.append("")
    lines.append(f"Updated: {now.strftime('%I:%M')}")

    return "\n".join(lines)


def get_clarkson_all():
    """Get Clarkson departures for BOTH trains and buses"""
    url = f"{BASE_URL}/Stop/NextService"

    now = datetime.now()
    result = {"from_clarkson": [], "from_union": []}

    # Get bus departures FROM Clarkson (stop code 00181) - going East to Union
    try:
        resp = requests.get(url, params={"key": API_KEY, "stopCode": "00181"}, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("Metadata", {}).get("ErrorCode") == "200":
                for dep in data.get("NextService", {}).get("Lines", []) or []:
                    direction = dep.get("DirectionName", "").strip()
                    computed = dep.get("ComputedDepartureTime", "")
                    # Filter: only show eastbound (Union Station), exclude Oakville
                    if computed and "Union" in direction:
                        dep_time = datetime.strptime(computed, "%Y-%m-%d %H:%M:%S")
                        mins = int((dep_time - now).total_seconds() / 60)
                        if mins >= 0:
                            dest = direction.replace("18L - ", "").strip()
                            result["from_clarkson"].append({"dest": dest, "mins": mins})
    except:
        pass

    # Get bus departures FROM Union (stop code 02300) - going to Clarkson/Oakville
    try:
        resp = requests.get(url, params={"key": API_KEY, "stopCode": "02300"}, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("Metadata", {}).get("ErrorCode") == "200":
                for dep in data.get("NextService", {}).get("Lines", []) or []:
                    direction = dep.get("DirectionName", "").strip()
                    computed = dep.get("ComputedDepartureTime", "")
                    # Filter for Route 18 buses going to Clarkson
                    if computed and ("18L" in dep.get("LineCode", "") or "18L" in dep.get("DirectionName", "")):
                        dep_time = datetime.strptime(computed, "%Y-%m-%d %H:%M:%S")
                        mins = int((dep_time - now).total_seconds() / 60)
                        if mins >= 0:
                            dest = direction.replace("18L - ", "").strip()
                            result["from_union"].append({"dest": dest, "mins": mins})
    except:
        pass

    return result


def format_clarkson_all():
    """Format Clarkson bus departures - Clarkson to Union AND Union to Clarkson"""
    data = get_clarkson_all()

    from_clarkson = sorted(data["from_clarkson"], key=lambda x: x["mins"])
    from_union = sorted(data["from_union"], key=lambda x: x["mins"])

    lines = ["🚌 Route 18L - Lakeshore West"]
    lines.append("")

    # From Clarkson → Union (Eastbound only)
    lines.append("From Clarkson GO (Eastbound):")
    if from_clarkson:
        for b in from_clarkson[:3]:
            lines.append(f"  → Union Station: {b['mins']} min")
    else:
        lines.append("  • No service")

    lines.append("")

    # From Union → Clarkson (Westbound)
    lines.append("From Union Station (Westbound):")
    if from_union:
        for b in from_union[:3]:
            lines.append(f"  → {b['dest']}: {b['mins']} min")
    else:
        lines.append("  • No service")

    lines.append("")
    lines.append(f"Updated: {datetime.now().strftime('%I:%M')}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys, subprocess, re

    # Check for --telegram flag
    send_telegram = "--telegram" in sys.argv
    args = [a for a in sys.argv if a != "--telegram"]

    if len(args) < 2:
        print("Usage: python3 metrolinx_tracker.py <station_code>")
        print("   or: python3 metrolinx_tracker.py train")
        print("   or: python3 metrolinx_tracker.py bus")
        print("   or: python3 metrolinx_tracker.py alerts")
        print("  python3 metrolinx_tracker.py stations # List all stations")
        print("  --telegram: send result to Telegram instead of printing")
        sys.exit(1)

    command = args[1].upper()

    if command == "HELP":
        print("Usage: python3 metrolinx_tracker.py <station_code>")
        print("   or: python3 metrolinx_tracker.py train")
        print("   or: python3 metrolinx_tracker.py bus")

    elif command == "TRAIN":
        result = format_both_directions()
        if send_telegram:
            subprocess.run(["/home/steve/.npm-global/bin/openclaw", "message", "send",
                "--channel", "telegram", "--target", "1355348", "--message", result],
                capture_output=True, timeout=15)
        else:
            print(result)
    
    elif command == "BUS":
        result = format_clarkson_all()
        if send_telegram:
            subprocess.run(["/home/steve/.npm-global/bin/openclaw", "message", "send",
                "--channel", "telegram", "--target", "1355348", "--message", result],
                capture_output=True, timeout=15)
        else:
            print(result)

    elif command == "BOTH":
        result = format_both_directions()
        if send_telegram:
            subprocess.run(["/home/steve/.npm-global/bin/openclaw", "message", "send",
                "--channel", "telegram", "--target", "1355348", "--message", result],
                capture_output=True, timeout=15)
        else:
            print(result)

    elif command == "ALERTS":
        print(check_service_alerts())

    elif command == "STATIONS":
        print("Available stations:")
        for s, code in sorted(STATIONS.items()):
            print(f"  {s}")

    else:
        station = STATIONS.get(command, command)
        departures = get_next_departures(command)
        print(format_departures(departures, station))
