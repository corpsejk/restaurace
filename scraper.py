import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import re


HOLISE_SCRIPT = Path("scraper_u_holise.py")
KOZLOVNA_SCRIPT = Path("scraper_kozlovna.py")

HOLISE_JSON = Path("u_holise.json")
KOZLOVNA_JSON = Path("kozlovna.json")

OUTPUT_FILE = Path("menu.json")


def convert_date_to_iso(date_text):
    """Převede např. Pátek 2.10.2026 na 2026-10-02."""

    match = re.search(
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})",
        date_text
    )

    if not match:
        raise ValueError(
            f"Nelze převést datum: {date_text}"
        )

    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))

    return f"{year:04d}-{month:02d}-{day:02d}"


def run_scraper(script, json_file, restaurant_name):
    """Spustí samostatný scraper a načte jeho JSON."""

    print()
    print("===================================")
    print(f"STAHUJI: {restaurant_name.upper()}")
    print("===================================")

    try:

        result = subprocess.run(
            [sys.executable, str(script)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        if result.stdout:
            print(result.stdout)

        if not json_file.exists():
            raise RuntimeError(
                f"Scraper nevytvořil soubor {json_file}"
            )

        with json_file.open(
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        return data

    except subprocess.CalledProcessError as e:

        print()
        print(f"!!! CHYBA {restaurant_name.upper()} !!!")

        if e.stdout:
            print(e.stdout)

        if e.stderr:
            print(e.stderr)

        return None

    except Exception as e:

        print()
        print(f"!!! CHYBA {restaurant_name.upper()} !!!")
        print(str(e))

        return None


def load_previous_menu():
    """Načte předchozí menu.json, pokud existuje."""

    if not OUTPUT_FILE.exists():
        return None

    try:

        with OUTPUT_FILE.open(
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print()
        print("!!! VAROVÁNÍ !!!")
        print(
            f"Předchozí menu.json se nepodařilo načíst: {e}"
        )

        return None


def find_previous_restaurant(previous_menu, restaurant_name):
    """Najde poslední známá data dané restaurace."""

    if not previous_menu:
        return None

    for restaurant in previous_menu.get(
        "restaurants",
        []
    ):

        if restaurant.get("restaurant") == restaurant_name:
            return restaurant

    return None


# =========================================================
# HLAVNÍ PROGRAM
# =========================================================

print()
print("###################################")
print("#        RESTAURACE SCRAPER       #")
print("###################################")


previous_menu = load_previous_menu()

restaurants = []
errors = []


# =========================================================
# U HOLIŠE
# =========================================================

holise = run_scraper(
    HOLISE_SCRIPT,
    HOLISE_JSON,
    "U Holiše"
)

if holise is not None:

    holise["date"] = convert_date_to_iso(
        holise["date"]
    )

    holise["status"] = "fresh"

    restaurants.append(holise)

else:

    previous = find_previous_restaurant(
        previous_menu,
        "U Holiše"
    )

    if previous:

        previous = previous.copy()
        previous["status"] = "stale"

        restaurants.append(previous)

        errors.append(
            "U Holiše – použita poslední známá data"
        )

    else:

        errors.append(
            "U Holiše – data nejsou dostupná"
        )


# =========================================================
# KOZLOVNA
# =========================================================

kozlovna = run_scraper(
    KOZLOVNA_SCRIPT,
    KOZLOVNA_JSON,
    "Holešovická Kozlovna"
)

if kozlovna is not None:

    kozlovna["date"] = convert_date_to_iso(
        kozlovna["date"]
    )

    kozlovna["status"] = "fresh"

    restaurants.append(kozlovna)

else:

    previous = find_previous_restaurant(
        previous_menu,
        "Holešovická Kozlovna"
    )

    if previous:

        previous = previous.copy()
        previous["status"] = "stale"

        restaurants.append(previous)

        errors.append(
            "Holešovická Kozlovna – "
            "použita poslední známá data"
        )

    else:

        errors.append(
            "Holešovická Kozlovna – data nejsou dostupná"
        )


# =========================================================
# KONTROLA
# =========================================================

if not restaurants:

    raise RuntimeError(
        "Nejsou dostupná žádná data."
    )


# =========================================================
# DATUM
# =========================================================

fresh_dates = {
    restaurant["date"]
    for restaurant in restaurants
    if restaurant.get("status") == "fresh"
}


if fresh_dates:

    menu_date = max(fresh_dates)

else:

    # Pokud dnes nefunguje ani jeden scraper,
    # zachováme datum z předchozího menu.

    if previous_menu and previous_menu.get("date"):

        menu_date = previous_menu["date"]

    else:

        raise RuntimeError(
            "Nelze určit datum menu."
        )


# =========================================================
# AKTUALIZACE
# =========================================================

updated_at = datetime.now(
    timezone.utc
).isoformat(
    timespec="seconds"
).replace(
    "+00:00",
    "Z"
)


# =========================================================
# VÝSLEDNÝ JSON
# =========================================================

menu = {
    "date": menu_date,
    "updated_at": updated_at,
    "restaurants": restaurants
}


# =========================================================
# ULOŽENÍ
# =========================================================

with OUTPUT_FILE.open(
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        menu,
        f,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# VÝPIS
# =========================================================

print()
print("===================================")
print("MENU.JSON VYTVOŘENO")
print("===================================")

print(f"Datum: {menu_date}")
print(f"Aktualizováno: {updated_at}")
print(f"Restaurace: {len(restaurants)}")
print(f"Soubor: {OUTPUT_FILE}")

print()
print("STAV:")

for restaurant in restaurants:

    status = restaurant.get(
        "status",
        "unknown"
    )

    print(
        f"  {restaurant['restaurant']}: {status}"
    )


if errors:

    print()
    print("VAROVÁNÍ:")

    for error in errors:
        print(f"  - {error}")