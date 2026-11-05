
import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = "https://stores.eintracht.de/tickets/info-service/parkplatz-prebooking/"
STATE = Path("state.json")

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def notify(message):
    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message},
        timeout=20
    )
    response.raise_for_status()

def get_tickets():
    response = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    available = {}
    rows_found = 0

    for row in soup.select("tr"):
        text = row.get_text(" ", strip=True)

        if not re.search(r"Eintracht Frankfurt\s*[-–]", text, re.I):
            continue

        rows_found += 1

        if re.search(r"noch keine tickets verfügbar", text, re.I):
            continue

        links = [
            a for a in row.find_all("a", href=True)
            if re.search(r"buchen|ticket", a.get_text(" ", strip=True), re.I)
        ]

        if links:
            key = re.sub(r"\s+", " ", text)
            link = urljoin(URL, links[0]["href"])
            available[key] = link

    if rows_found == 0:
        raise RuntimeError("Keine Spieltabelle erkannt!")

    return available

def main():
    current = get_tickets()

    if not STATE.exists():
        STATE.write_text(json.dumps(current, ensure_ascii=False, indent=2))
        notify(
            "✅ Eintracht Parkplatz-Alarm aktiviert!\n"
            f"Bereits buchbare Einträge: {len(current)}\n"
            "Neue Buchungsmöglichkeiten werden gemeldet."
        )
        return

    previous = json.loads(STATE.read_text())

    for game, link in current.items():
        if game not in previous:
            notify(
                "🚨 NEUE EINTRACHT-PARKTICKETS!\n\n"
                f"{game}\n\n"
                f"Jetzt buchen:\n{link}"
            )

    STATE.write_text(json.dumps(current, ensure_ascii=False, indent=2))
    print(f"Prüfung erfolgreich: {len(current)} buchbare Einträge")

if __name__ == "__main__":
    main()
