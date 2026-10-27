import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.holesovickakozlovna.cz/"
OUTPUT = Path("kozlovna.json")
DEBUG_HTML = Path("debug_kozlovna.html")

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


def find_line(lines, pattern, start=0):
    """Index prvního řádku, který celý odpovídá regulárnímu výrazu.

    Hledání je tolerantní: nezáleží na velikosti písmen a regulární výraz
    si poradí s drobnými změnami (např. mezera před dvojtečkou).
    """
    rx = re.compile(pattern, re.IGNORECASE)

    for i in range(start, len(lines)):
        if rx.fullmatch(lines[i]):
            return i

    return None


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

    # ---- Hranice sekcí (tolerantně k mezerám a dvojtečce)
    i_soups = find_line(lines, r"Polévky\s*:?")
    i_mains = find_line(lines, r"Hlavní\s+jídla\s*:?", (i_soups or 0) + 1)
    i_end = find_line(
        lines, r"Holešovická Kozlovna využívá\s+služby", (i_mains or 0) + 1
    )
    if i_end is None:
        i_end = len(lines)

    # ---- Polévky
    soups = []

    if i_soups is not None:
        i = i_soups + 1
        stop = i_mains if i_mains is not None else i_end

        while i < stop:
            line = lines[i]

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

    if i_mains is not None:
        start = i_mains + 1

        for i in range(start, i_end):
            price_single, price_menu = parse_price(lines[i])

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

    # ---- Kontroly (při selhání se uloží HTML pro rozbor)
    problem = None

    if not date:
        problem = "nenalezeno datum menu"
    elif not soups:
        problem = "nenalezeny žádné polévky"
    elif not main_dishes:
        problem = "nenalezena žádná hlavní jídla"

    if problem:
        DEBUG_HTML.write_text(html, encoding="utf-8")
        raise RuntimeError(
            f"Kozlovna: {problem} "
            f"(sekce polévky={i_soups}, hlavní jídla={i_mains}, "
            f"řádků={len(lines)}). HTML uloženo do {DEBUG_HTML}."
        )

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
