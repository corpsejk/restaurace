import re
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.holesovickakozlovna.cz/"

response = requests.get(URL, timeout=20)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

text = soup.get_text("\n", strip=True)
lines = [line.strip() for line in text.splitlines() if line.strip()]

# ---------------------------------------------------------
# Pomocné funkce
# ---------------------------------------------------------

def parse_price(price_text):
    """
    Převod:
        195/225 Kč -> 195, 225
        209 Kč     -> 209, None
    """
    match = re.search(r"(\d+)\s*(?:/\s*(\d+))?\s*Kč", price_text)

    if not match:
        return None, None

    price_single = int(match.group(1))
    price_menu = int(match.group(2)) if match.group(2) else None

    return price_single, price_menu


def parse_dish_name(name):
    """
    Oddělí alergeny a poznámku od názvu jídla.
    """

    note = None

    if "Omezený počet" in name:
        note = "Omezený počet"
        name = re.sub(r"\(\s*Omezený počet\s*\)", "", name)

    allergens = None

    # Alergeny jsou poslední závorka ve tvaru např. (1,3,7,9)
    match = re.search(r"\(([\d,\s]+)\)\s*$", name)

    if match:
        allergens = match.group(1).replace(" ", "")
        name = name[:match.start()].strip()

    return name.strip(), allergens, note


# ---------------------------------------------------------
# Datum
# ---------------------------------------------------------

date = None

for line in lines:
    if re.match(
        r"^(Pondělí|Úterý|Středa|Čtvrtek|Pátek|Sobota|Neděle)",
        line
    ):
        date = line
        break


# ---------------------------------------------------------
# Polévky
# ---------------------------------------------------------

soups = []

try:
    soup_start = lines.index("Polévky :") + 1
except ValueError:
    soup_start = None

if soup_start is not None:
    i = soup_start

    while i < len(lines):
        line = lines[i]

        if line == "Hlavní jídla :":
            break

        # cena je vždy na následujícím řádku
        if i + 1 < len(lines) and re.fullmatch(r"\d+\s*Kč", lines[i + 1]):
            name = line
            price = int(re.search(r"\d+", lines[i + 1]).group())

            soup_name, allergens, note = parse_dish_name(name)

            soups.append({
                "name": soup_name,
                "price": price,
                "allergens": allergens,
                "note": note
            })

            i += 2
        else:
            i += 1


# ---------------------------------------------------------
# Hlavní jídla
# ---------------------------------------------------------

main_dishes = []

try:
    main_start = lines.index("Hlavní jídla :") + 1
except ValueError:
    main_start = None

if main_start is not None:
    i = main_start

    while i < len(lines):
        line = lines[i]

        # konec hlavních jídel
        if line == "Holešovická Kozlovna využívá služby":
            break

        # hledáme řádek s cenou
        price_single, price_menu = parse_price(line)

        if price_single is not None:

            # název je předchozí řádek
            if main_dishes or i > main_start:
                name = lines[i - 1]

                dish_name, allergens, note = parse_dish_name(name)

                main_dishes.append({
                    "name": dish_name,
                    "price_single": price_single,
                    "price_menu": price_menu,
                    "allergens": allergens,
                    "note": note
                })

        i += 1


# ---------------------------------------------------------
# Výsledná struktura
# ---------------------------------------------------------

menu = {
    "restaurant": "Holešovická Kozlovna",
    "date": date,
    "soups": soups,
    "main_dishes": main_dishes
}


# ---------------------------------------------------------
# Výpis
# ---------------------------------------------------------

print(json.dumps(menu, ensure_ascii=False, indent=2))


# ---------------------------------------------------------
# Uložení do souboru
# ---------------------------------------------------------

with open("kozlovna.json", "w", encoding="utf-8") as f:
    json.dump(menu, f, ensure_ascii=False, indent=2)