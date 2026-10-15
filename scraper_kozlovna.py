import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.holesovickakozlovna.cz/"
OUTPUT = Path("kozlovna.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "cs-CZ,cs;q=0.9",
}

DAYS = "Pondělí|Úterý|Středa|Čtvrtek|Pátek|Sobota|Neděle"


def fetch_html(retries=3):
    """Stáhne stránku, při chybě to zkusí znovu."""
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(URL, headers=HEADERS, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            last_error = e
            if attempt < retries:
                time.sleep(3 * attempt)

    raise RuntimeError(f"Kozlovnu se nepodařilo stáhnout: {last_error}")


def parse_price(price_text):
    """195/225 Kč -> (195, 225); 209 Kč -> (209, None)."""
    match = re.search(r"(\d+)\s*(?:/\s*(\d+))?\s*Kč", price_text)

    if not match:
        return None, None

    price_single = int(match.group(1))
    price_menu = int(match.group(2)) if match.group(2) else None

    return price_single, price_menu


def parse_dish_name(name):
    """Oddělí alergeny a poznámku od názvu jídla."""
    note = None

    if "Omezený počet" in name:
        note = "Omezený počet"
        name = re.sub(r"\(\s*Omezený počet\s*\)", "", name)

    allergens = None
    match = re.search(r"\(([\d,\s]+)\)\s*$", name.strip())

    if match:
        allergens = match.group(1).replace(" ", "")
        name = name.strip()[:match.start()]

    return name.strip(), allergens, note


def scrape():
    """Vrátí slovník s menu Kozlovny. Při problému vyhodí výjimku."""
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # ---- Datum (musí obsahovat i číslo, aby se nespletlo s otevírací dobou)
    date = None
    date_re = re.compile(rf"^({DAYS})\s+\d{{1,2}}\.\s*\d{{1,2}}\.\s*\d{{4}}")

    for line in lines:
        if date_re.match(line):
            date = line
            break

    # ---- Polévky
    soups = []

    if "Polévky :" in lines:
        i = lines.index("Polévky :") + 1

        while i < len(lines):
            line = lines[i]

            if line == "Hlavní jídla :":
                break

            if i + 1 < len(lines) and re.fullmatch(r"\d+\s*Kč", lines[i + 1]):
                price = int(re.search(r"\d+", lines[i + 1]).group())
                soup_name, allergens, note = parse_dish_name(line)

                soups.append({
                    "name": soup_name,
                    "price": price,
                    "allergens": allergens,
                    "note": note,
                })
                i += 2
            else:
                i += 1

    # ---- Hlavní jídla
    main_dishes = []

    if "Hlavní jídla :" in lines:
        start = lines.index("Hlavní jídla :") + 1

        for i in range(start, len(lines)):
            line = lines[i]

            if line == "Holešovická Kozlovna využívá služby":
                break

            price_single, price_menu = parse_price(line)

            if price_single is None or i - 1 < start:
                continue

            dish_name, allergens, note = parse_dish_name(lines[i - 1])

            main_dishes.append({
                "name": dish_name,
                "price_single": price_single,
                "price_menu": price_menu,
                "allergens": allergens,
                "note": note,
            })

    # ---- Kontroly
    if not date:
        raise RuntimeError("Kozlovna: nenalezeno datum menu.")
    if not soups:
        raise RuntimeError("Kozlovna: nenalezeny žádné polévky.")
    if not main_dishes:
        raise RuntimeError("Kozlovna: nenalezena žádná hlavní jídla.")

    return {
        "restaurant": "Holešovická Kozlovna",
        "date": date,
        "soups": soups,
        "main_dishes": main_dishes,
    }


if __name__ == "__main__":
    # Samostatné spuštění pro ladění: vypíše menu a uloží kozlovna.json
    menu = scrape()
    print(json.dumps(menu, ensure_ascii=False, indent=2))
    OUTPUT.write_text(
        json.dumps(menu, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
