import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


URL = "https://restauraceuholise.cz/cs/denni-menu/lacarte"
OUTPUT = Path("u_holise.json")


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_name(name):
    return clean_text(name).upper()


def extract_price(text):
    text = clean_text(text)

    match = re.search(r"(\d+)\s*Kč", text)

    if match:
        return int(match.group(1))

    return None


def extract_allergens(wrapper):
    """
    Získá alergeny z textu wrapperu.

    Cena (např. 49, 195, 200) se ignoruje.
    Podporované kódy jsou např.:
    1, 1a, 3, 7, 8, 9, 10, 12
    """

    text = wrapper.get_text(" ", strip=True)
    text = clean_text(text)

    # Odstraníme ceny z textu.
    text = re.sub(r"\b\d+\s*Kč\b", "", text)

    # Alergeny.
    matches = re.findall(
        r"\b\d+[a-z]?\b",
        text,
        flags=re.IGNORECASE
    )

    result = []

    for item in matches:

        item = item.lower()

        # Povolené kódy alergenů.
        if item not in (
            "1",
            "1a",
            "1b",
            "1c",
            "1d",
            "1e",
            "1f",
            "1g",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
        ):
            continue

        if item not in result:
            result.append(item)

    return ",".join(result) if result else None


def main():

    # =========================================================
    # NAČTENÍ STRÁNKY PŘES PLAYWRIGHT
    # =========================================================

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        response = page.goto(
            URL,
            wait_until="networkidle"
        )

        if not response:
            raise RuntimeError(
                "Stránka nevrátila žádnou odpověď."
            )

        if response.status != 200:
            raise RuntimeError(
                f"U Holiše vrátilo HTTP {response.status}"
            )

        html = page.content()

        browser.close()

    # =========================================================
    # PARSOVÁNÍ HTML
    # =========================================================

    soup = BeautifulSoup(html, "html.parser")

    # =========================================================
    # DATUM
    # =========================================================

    date = None

    heading = soup.find("h3")

    if heading:

        heading_text = clean_text(
            heading.get_text(" ", strip=True)
        )

        match = re.search(
            r"(\d{1,2}\.\d{1,2}\.\d{4})",
            heading_text
        )

        if match:
            date = match.group(1)

    # =========================================================
    # MENU BLOKY
    # =========================================================

    wrappers = soup.select(".lc_block_wrapper")

    if not wrappers:
        raise RuntimeError(
            "Nebyly nalezeny žádné .lc_block_wrapper bloky."
        )

    soups = []
    main_dishes = []

    # Cena zvýhodněného menu podle názvu jídla
    menu_prices = {}

    current_category = None

    # =========================================================
    # ZPRACOVÁNÍ BLOKŮ
    # =========================================================

    for wrapper in wrappers:

        category_el = wrapper.select_one(
            ".lc_block_line_category_text"
        )

        item_el = wrapper.select_one(
            ".lc_block_line_item_text"
        )

        price_el = wrapper.select_one(
            ".lc_block_line_price_text"
        )

        category = None

        if category_el:

            category = clean_text(
                category_el.get_text(" ", strip=True)
            )

        item = None

        if item_el:

            item = clean_text(
                item_el.get_text(" ", strip=True)
            )

        price = None

        if price_el:

            price = extract_price(
                price_el.get_text(" ", strip=True)
            )

        # -----------------------------------------------------
        # NOVÁ KATEGORIE
        # -----------------------------------------------------

        if category and category != "-":
            current_category = category.upper()

        # -----------------------------------------------------
        # POLÉVKY
        # -----------------------------------------------------

        if current_category == "POLÉVKA":

            if item:

                soups.append({
                    "name": item,
                    "price": price,
                    "allergens": extract_allergens(wrapper),
                    "note": None
                })

        # -----------------------------------------------------
        # ZVÝHODNĚNÉ MENU
        # -----------------------------------------------------

        elif current_category in (
            "ZVÝHODNĚNÉ MENU JEDNA",
            "ZVÝHODNĚNÉ MENU DVA"
        ):

            if not item:
                continue

            normalized = normalize_name(item)

            # POLÉVKA DLE VÝBĚRU ignorujeme
            if normalized == "POLÉVKA DLE VÝBĚRU":
                continue

            # Limonádu ignorujeme
            if "TOČENÁ LIMONÁDA" in normalized:

                # Cena v tomto bloku patří
                # předchozímu jídlu zvýhodněného menu.

                if price is not None:
                    if "menu_dish" in locals() and menu_dish:
                        menu_prices[
                            normalize_name(menu_dish)
                        ] = price

                        menu_dish = None

                continue

            # Toto je hlavní jídlo zvýhodněného menu.
            menu_dish = item

        # -----------------------------------------------------
        # HLAVNÍ CHODY
        # -----------------------------------------------------

        elif current_category == "HLAVNÍ CHODY":

            if item:

                main_dishes.append({
                    "name": item,
                    "price_single": price,
                    "price_menu": None,
                    "allergens": extract_allergens(wrapper),
                    "note": None
                })

    # =========================================================
    # PŘIŘAZENÍ CEN MENU K HLAVNÍM JÍDLŮM
    # =========================================================

    for dish in main_dishes:

        key = normalize_name(dish["name"])

        if key in menu_prices:
            dish["price_menu"] = menu_prices[key]

    # =========================================================
    # VÝSLEDNÝ JSON
    # =========================================================

    result = {
        "restaurant": "U Holiše",
        "date": date,
        "soups": soups,
        "main_dishes": main_dishes
    }

    # =========================================================
    # KONTROLY
    # =========================================================

    if not soups:
        raise RuntimeError(
            "Nepodařilo se najít žádné polévky."
        )

    if not main_dishes:
        raise RuntimeError(
            "Nepodařilo se najít žádná hlavní jídla."
        )

    # =========================================================
    # ULOŽENÍ
    # =========================================================

    OUTPUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # =========================================================
    # VÝPIS
    # =========================================================

    print()
    print("===================================")
    print("U HOLIŠE – MENU NALEZENO")
    print("===================================")
    print(f"Datum: {date}")
    print()

    print("POLÉVKY:")

    for soup in soups:

        print(
            f"  {soup['name']} — "
            f"{soup['price']} Kč"
        )

    print()

    print("HLAVNÍ CHODY:")

    for dish in main_dishes:

        print(f"  {dish['name']}")

        print(
            f"    samostatně: "
            f"{dish['price_single']} Kč"
        )

        menu_price = dish["price_menu"]

        if menu_price is None:
            menu_text = "—"
        else:
            menu_text = f"{menu_price} Kč"

        print(
            f"    menu: {menu_text}"
        )

    print()
    print(f"Uloženo do: {OUTPUT}")
    print()


if __name__ == "__main__":
    main()