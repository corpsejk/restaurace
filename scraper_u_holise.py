import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

URL = "https://restauraceuholise.cz/cs/denni-menu/lacarte"
OUTPUT = Path("u_holise.json")
DEBUG_HTML = Path("debug_u_holise.html")

ALLOWED_ALLERGENS = {
    "1", "1a", "1b", "1c", "1d", "1e", "1f", "1g",
    "2", "3", "4", "5", "6", "7",
    "8", "9", "10", "11", "12", "13", "14",
}


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_name(name):
    return clean_text(name).upper()


def category_kind(category):
    """Určí typ sekce podle názvu kategorie (tolerantně k drobným změnám).

    Vrací "soup", "menu", "main" nebo None, když kategorii neznáme.
    """
    c = normalize_name(category)

    if c.startswith("POLÉVK"):
        return "soup"
    if c.startswith("ZVÝHODNĚNÉ MENU"):
        return "menu"
    if c.startswith("HLAVNÍ"):
        return "main"

    return None


def extract_price(text):
    match = re.search(r"(\d+)\s*Kč", clean_text(text))
    return int(match.group(1)) if match else None


def extract_allergens(wrapper):
    """Získá kódy alergenů z textu bloku (ceny se ignorují)."""
    text = clean_text(wrapper.get_text(" ", strip=True))
    text = re.sub(r"\b\d+\s*Kč\b", "", text)

    result = []

    for item in re.findall(r"\b\d+[a-z]?\b", text, flags=re.IGNORECASE):
        item = item.lower()

        if item in ALLOWED_ALLERGENS and item not in result:
            result.append(item)

    return ",".join(result) if result else None


def download_html():
    """Načte stránku přes Playwright a vrátí HTML s vykresleným menu."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        try:
            page = browser.new_page()

            response = page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            if response is None or not response.ok:
                status = response.status if response else "žádná odpověď"
                raise RuntimeError(f"U Holiše: HTTP {status}")

            # Menu se doplňuje JavaScriptem, počkáme na první blok.
            try:
                page.wait_for_selector(".lc_block_wrapper", timeout=20000)
            except PlaywrightTimeout:
                raise RuntimeError(
                    "U Holiše: menu se na stránce neobjevilo."
                )

            return page.content()
        finally:
            browser.close()


def scrape():
    """Vrátí slovník s menu U Holiše. Při problému vyhodí výjimku."""
    html = download_html()
    soup = BeautifulSoup(html, "html.parser")

    # ---- Datum (první nadpis, který obsahuje datum)
    date = None

    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        match = re.search(
            r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})",
            clean_text(heading.get_text(" ", strip=True)),
        )
        if match:
            date = match.group(1)
            break

    # ---- Bloky menu
    wrappers = soup.select(".lc_block_wrapper")

    if not wrappers:
        DEBUG_HTML.write_text(html, encoding="utf-8")
        raise RuntimeError(
            "U Holiše: nenalezeny žádné bloky menu. "
            f"HTML uloženo do {DEBUG_HTML}."
        )

    soups = []
    main_dishes = []
    menu_prices = {}          # cena zvýhodněného menu podle názvu jídla
    current_category = None
    seen_categories = []      # pro diagnostiku při chybě
    menu_dish = None          # poslední hlavní jídlo ze zvýhodněného menu

    for wrapper in wrappers:
        category_el = wrapper.select_one(".lc_block_line_category_text")
        item_el = wrapper.select_one(".lc_block_line_item_text")
        price_el = wrapper.select_one(".lc_block_line_price_text")

        category = clean_text(category_el.get_text(" ", strip=True)) if category_el else None
        item = clean_text(item_el.get_text(" ", strip=True)) if item_el else None
        price = extract_price(price_el.get_text(" ", strip=True)) if price_el else None

        if category and category != "-":
            current_category = category.upper()

            if current_category not in seen_categories:
                seen_categories.append(current_category)

        kind = category_kind(current_category) if current_category else None

        if kind == "soup":
            if item:
                soups.append({
                    "name": item,
                    "price": price,
                    "allergens": extract_allergens(wrapper),
                    "note": None,
                })

        elif kind == "menu":
            if not item:
                continue

            normalized = normalize_name(item)

            if normalized == "POLÉVKA DLE VÝBĚRU":
                continue

            if "TOČENÁ LIMONÁDA" in normalized:
                # Cena v tomto bloku patří předchozímu jídlu menu.
                if price is not None and menu_dish:
                    menu_prices[normalize_name(menu_dish)] = price
                    menu_dish = None
                continue

            menu_dish = item

        elif kind == "main":
            if item:
                main_dishes.append({
                    "name": item,
                    "price_single": price,
                    "price_menu": None,
                    "allergens": extract_allergens(wrapper),
                    "note": None,
                })

    # ---- Přiřazení cen menu k hlavním jídlům
    for dish in main_dishes:
        key = normalize_name(dish["name"])

        if key in menu_prices:
            dish["price_menu"] = menu_prices[key]

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
            f"U Holiše: {problem} "
            f"(bloků={len(wrappers)}, kategorie={seen_categories}). "
            f"HTML uloženo do {DEBUG_HTML}."
        )

    return {
        "restaurant": "U Holiše",
        "date": date,
        "soups": soups,
        "main_dishes": main_dishes,
    }


if __name__ == "__main__":
    # Samostatné spuštění pro ladění: vypíše menu a uloží u_holise.json
    menu = scrape()
    print(json.dumps(menu, ensure_ascii=False, indent=2))
    OUTPUT.write_text(
        json.dumps(menu, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
