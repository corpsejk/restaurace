"""
Stáhne menu obou restaurací a uloží menu.json.

Pravidla:
  * restaurace se zobrazí jako "fresh" jen tehdy, když datum na jejím webu
    odpovídá dnešnímu dni (pražský čas),
  * jinak (chyba, prázdná stránka, včerejší menu) je "unavailable",
  * pokud už dnes menu úspěšně získáno bylo a pozdější běh selže,
    zůstane dnešní menu zachováno.
menu.json se přepíše jen když se obsah změnil (méně zbytečných commitů).

Chyby scraperů:
  * menu.json se vždy nejdřív uloží (úspěšná restaurace se zobrazí),
  * pokud scraper SELHAL (výjimka) a restaurace skončila bez dnešního menu,
    skript skončí s kódem 1, takže workflow na GitHubu selže a přijde e-mail,
  * alarm se ale spustí až od ALERT_FROM (výchozí 10:30 pražského času), aby
    nechodily falešné poplachy, když menu ještě prostě nebylo zveřejněno.
    Dá se přepsat proměnnou prostředí ALERT_FROM (např. ALERT_FROM=00:00).
  * Menu z jiného dne (stránka funguje, jen není aktualizovaná) chyba není.
"""

import json
import os
import re
import sys
import traceback
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import scraper_kozlovna
import scraper_u_holise

PRAGUE = ZoneInfo("Europe/Prague")
OUTPUT_FILE = Path("menu.json")


def _parse_alert_from():
    """Čas (HH:MM, pražský), od kterého se selhání scraperu hlásí jako chyba."""
    raw = os.environ.get("ALERT_FROM", "10:30")

    try:
        hour, minute = (int(x) for x in raw.split(":"))
        return time(hour, minute)
    except ValueError:
        print(f"VAROVÁNÍ: neplatné ALERT_FROM={raw!r}, používám 10:30")
        return time(10, 30)


ALERT_FROM = _parse_alert_from()

RESTAURANTS = [
    ("U Holiše", scraper_u_holise.scrape),
    ("Holešovická Kozlovna", scraper_kozlovna.scrape),
]


def convert_date_to_iso(date_text):
    """'Pátek 2.10.2026' nebo '2. 10. 2026' -> '2026-10-02'; jinak None."""
    if not date_text:
        return None

    match = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", date_text)

    if not match:
        return None

    day, month, year = (int(g) for g in match.groups())

    return f"{year:04d}-{month:02d}-{day:02d}"


def load_previous_menu():
    if not OUTPUT_FILE.exists():
        return None

    try:
        return json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"VAROVÁNÍ: předchozí menu.json nelze načíst: {e}")
        return None


def find_previous_restaurant(previous_menu, name):
    if not previous_menu:
        return None

    for restaurant in previous_menu.get("restaurants", []):
        if restaurant.get("restaurant") == name:
            return restaurant

    return None


def unavailable_entry(name, today):
    return {
        "restaurant": name,
        "date": today,
        "soups": [],
        "main_dishes": [],
        "status": "unavailable",
    }


def get_restaurant(name, scrape, today, previous_menu):
    """Vrátí (záznam restaurace, chyba).

    chyba je text výjimky, jen pokud scraper selhal A restaurace skončila bez
    dnešního menu. Jinak je None.
    """
    print()
    print("=" * 40)
    print(f"STAHUJI: {name.upper()}")
    print("=" * 40)

    data = None
    error = None

    try:
        data = scrape()
    except Exception as e:
        error = " ".join(str(e).split()) or type(e).__name__
        print(f"CHYBA: {e}")
        print(f"::error title=Scraper {name}::{error}")
        traceback.print_exc()

    if data:
        iso = convert_date_to_iso(data.get("date"))

        if iso == today:
            data["restaurant"] = name
            data["date"] = today
            data["status"] = "fresh"
            print(
                f"OK: {len(data['soups'])} polévek, "
                f"{len(data['main_dishes'])} hlavních jídel"
            )
            return data, None

        print(f"Menu na webu je z jiného dne ({data.get('date')}), nepoužito.")

    # Dnešní menu jsme už možná získali dřívějším během.
    previous = find_previous_restaurant(previous_menu, name)

    if (
        previous
        and previous.get("date") == today
        and previous.get("status") == "fresh"
    ):
        print("Ponechávám dnešní menu z dřívějšího běhu.")
        return previous, None

    print("Dnešní menu zatím není k dispozici.")
    return unavailable_entry(name, today), error


def exit_code_for(failures, now):
    """0 = vše v pořádku (nebo ještě brzy na alarm), 1 = scraper je rozbitý."""
    if not failures:
        return 0

    print()
    print("=" * 40)
    print("SELHÁNÍ SCRAPERU")
    print("=" * 40)

    for failure in failures:
        print(f"  {failure}")

    if now.time() < ALERT_FROM:
        print(
            f"Je před {ALERT_FROM:%H:%M}, chyba se zatím jen eviduje "
            "(menu mohlo být prostě ještě nezveřejněno)."
        )
        return 0

    return 1


def main(now=None):
    now = now or datetime.now(PRAGUE)
    today = now.date().isoformat()
    previous_menu = load_previous_menu()

    restaurants = []
    failures = []

    for name, scrape in RESTAURANTS:
        entry, error = get_restaurant(name, scrape, today, previous_menu)
        restaurants.append(entry)

        if error:
            failures.append(f"{name}: {error}")

    exit_code = exit_code_for(failures, now)

    # Pokud se nic nezměnilo (kromě času), soubor nepřepisujeme.
    if (
        previous_menu
        and previous_menu.get("date") == today
        and previous_menu.get("restaurants") == restaurants
    ):
        print()
        print("Menu se nezměnilo, menu.json zůstává beze změny.")
        return exit_code

    updated_at = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )

    menu = {
        "date": today,
        "updated_at": updated_at,
        "restaurants": restaurants,
    }

    OUTPUT_FILE.write_text(
        json.dumps(menu, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 40)
    print("MENU.JSON ULOŽENO")
    print("=" * 40)
    print(f"Datum: {today}")
    print(f"Aktualizováno: {updated_at}")

    for restaurant in restaurants:
        print(f"  {restaurant['restaurant']}: {restaurant['status']}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
