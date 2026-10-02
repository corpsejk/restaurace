/* =========================================================
   ALERGENY
   ========================================================= */

const allergenData = {

    "1": {
        title: "1 – Obiloviny obsahující lepek",
        description:
            "Obiloviny obsahující lepek: pšenice, žito, ječmen, oves, špalda, kamut a jejich hybridní odrůdy."
    },

    "1a": {
        title: "1a – Pšenice",
        description:
            "Pšenice a výrobky z ní."
    },

    "1b": {
        title: "1b – Žito",
        description:
            "Žito a výrobky z něj."
    },

    "1c": {
        title: "1c – Ječmen",
        description:
            "Ječmen a výrobky z něj."
    },

    "1d": {
        title: "1d – Oves",
        description:
            "Oves a výrobky z něj."
    },

    "1e": {
        title: "1e – Špalda",
        description:
            "Špalda a výrobky z ní."
    },

    "1f": {
        title: "1f – Kamut",
        description:
            "Kamut a výrobky z něj."
    },

    "1g": {
        title: "1g – Hybridní odrůdy",
        description:
            "Hybridní odrůdy obilovin obsahující gluten."
    },

    "2": {
        title: "2 – Korýši",
        description:
            "Korýši a výrobky z nich."
    },

    "3": {
        title: "3 – Vejce",
        description:
            "Vejce a výrobky z nich."
    },

    "4": {
        title: "4 – Ryby",
        description:
            "Ryby a výrobky z nich."
    },

    "5": {
        title: "5 – Arašídy",
        description:
            "Jádra podzemnice olejné (arašídy) a výrobky z nich."
    },

    "6": {
        title: "6 – Sójové boby",
        description:
            "Sójové boby a výrobky z nich."
    },

    "7": {
        title: "7 – Mléko",
        description:
            "Mléko a výrobky z něj, včetně laktózy."
    },

    "8": {
        title: "8 – Skořápkové plody",
        description:
            "Skořápkové plody: mandle, lískové ořechy, vlašské ořechy, kešu, pekanové ořechy, para ořechy, pistácie a makadamové ořechy."
    },

    "8a": {
        title: "8a – Mandle",
        description:
            "Mandle a výrobky z nich."
    },

    "8b": {
        title: "8b – Lískové ořechy",
        description:
            "Lískové ořechy a výrobky z nich."
    },

    "8c": {
        title: "8c – Vlašské ořechy",
        description:
            "Vlašské ořechy a výrobky z nich."
    },

    "8d": {
        title: "8d – Kešu ořechy",
        description:
            "Kešu ořechy a výrobky z nich."
    },

    "8e": {
        title: "8e – Pekanové ořechy",
        description:
            "Pekanové ořechy a výrobky z nich."
    },

    "8f": {
        title: "8f – Para ořechy",
        description:
            "Para ořechy a výrobky z nich."
    },

    "8g": {
        title: "8g – Pistácie",
        description:
            "Pistácie a výrobky z nich."
    },

    "8h": {
        title: "8h – Makadamie",
        description:
            "Makadamové ořechy a výrobky z nich."
    },

    "9": {
        title: "9 – Celer",
        description:
            "Celer a výrobky z něj."
    },

    "10": {
        title: "10 – Hořčice",
        description:
            "Hořčice a výrobky z ní."
    },

    "11": {
        title: "11 – Sezamová semena",
        description:
            "Sezamová semena a výrobky z nich."
    },

    "12": {
        title: "12 – Oxid siřičitý a siřičitany",
        description:
            "Oxid siřičitý a siřičitany v koncentracích vyšších než 10 mg/kg nebo 10 mg/l, vyjádřeno jako SO₂."
    },

    "13": {
        title: "13 – Vlčí bob (lupina)",
        description:
            "Vlčí bob (lupina) a výrobky z něj."
    },

    "14": {
        title: "14 – Měkkýši",
        description:
            "Měkkýši a výrobky z nich."
    }
};


/* =========================================================
   ODKAZY NA WEBY RESTAURACÍ
   ========================================================= */

const restaurantUrls = {

    "U Holiše":
        "https://restauraceuholise.cz/cs/denni-menu/lacarte",

    "Holešovická Kozlovna":
        "https://www.holesovickakozlovna.cz/"
};


/* =========================================================
   NAČTENÍ MENU
   ========================================================= */

async function loadMenu() {

    const restaurantsElement =
        document.getElementById("restaurants");

    const dateElement =
        document.getElementById("date");

    const updatedElement =
        document.getElementById("updated");


    try {

        const response = await fetch(
            "menu.json?" + Date.now()
        );

        if (!response.ok) {
            throw new Error(
                "HTTP chyba " + response.status
            );
        }

        const menu =
            await response.json();


        dateElement.textContent =
            formatDate(menu.date);


        if (menu.updated_at) {

            updatedElement.textContent =
                "Aktualizováno: " +
                formatDateTime(menu.updated_at);

        } else {

            updatedElement.textContent = "";

        }


        restaurantsElement.innerHTML = "";


        if (
            !menu.restaurants ||
            menu.restaurants.length === 0
        ) {

            restaurantsElement.innerHTML =
                '<div class="no-menu">Menu není k dispozici.</div>';

            return;
        }


        for (const restaurant of menu.restaurants) {

            const card =
                createRestaurantCard(restaurant);

            restaurantsElement.appendChild(card);
        }


        setupAllergenTooltips();

    }

    catch (error) {

        console.error(
            "Chyba při načítání menu:",
            error
        );

        dateElement.textContent =
            "Menu se nepodařilo načíst.";

        updatedElement.textContent = "";

        restaurantsElement.innerHTML =
            '<div class="no-menu">Nepodařilo se načíst menu.</div>';
    }
}


/* =========================================================
   KARTA RESTAURACE
   ========================================================= */

function createRestaurantCard(restaurant) {

    const card =
        document.createElement("section");

    card.className =
        "restaurant";


    const header =
        document.createElement("div");

    header.className =
        "restaurant-header";


    const title =
        document.createElement("h2");


    const link =
        document.createElement("a");


    link.href =
        restaurantUrls[restaurant.restaurant] || "#";

    link.target =
        "_blank";

    link.rel =
        "noopener noreferrer";

    link.textContent =
        restaurant.restaurant;


    title.appendChild(link);

    header.appendChild(title);

    card.appendChild(header);


    const content =
        document.createElement("div");

    content.className =
        "restaurant-content";


    if (restaurant.stale) {

        const warning =
            document.createElement("div");

        warning.className =
            "stale-warning";

        warning.textContent =
            "Upozornění: menu se nepodařilo aktuálně načíst. Zobrazuji poslední známé údaje.";

        content.appendChild(warning);
    }


    if (
        restaurant.soups &&
        restaurant.soups.length > 0
    ) {

        content.appendChild(
            createSoupsSection(
                restaurant.soups
            )
        );
    }


    if (
        restaurant.main_dishes &&
        restaurant.main_dishes.length > 0
    ) {

        content.appendChild(
            createMainDishesSection(
                restaurant.main_dishes
            )
        );
    }


    card.appendChild(content);


    return card;
}


/* =========================================================
   SEKCE POLÉVKY
   ========================================================= */

function createSoupsSection(soups) {

    const section =
        document.createElement("section");

    section.className =
        "menu-section";


    const heading =
        document.createElement("h3");

    heading.textContent =
        "Polévky";

    section.appendChild(heading);


    const table =
        document.createElement("table");


    const tbody =
        document.createElement("tbody");


    for (const soup of soups) {

        const row =
            document.createElement("tr");


        const nameCell =
            document.createElement("td");


        const name =
            document.createElement("strong");

        name.textContent =
            soup.name;

        nameCell.appendChild(name);


        if (soup.allergens) {

            const allergens =
                document.createElement("div");

            allergens.className =
                "allergens";

            allergens.appendChild(
                createAllergenLinks(
                    soup.allergens
                )
            );

            nameCell.appendChild(allergens);
        }


        if (soup.note) {

            const note =
                document.createElement("div");

            note.className =
                "dish-note";

            note.textContent =
                soup.note;

            nameCell.appendChild(note);
        }


        row.appendChild(nameCell);


        const priceCell =
            document.createElement("td");

        priceCell.className =
            "price";


        if (soup.price != null) {

            priceCell.textContent =
                soup.price + " Kč";
        }


        row.appendChild(priceCell);

        tbody.appendChild(row);
    }


    table.appendChild(tbody);

    section.appendChild(table);


    return section;
}


/* =========================================================
   SEKCE HLAVNÍ JÍDLA
   ========================================================= */

function createMainDishesSection(dishes) {

    const section =
        document.createElement("section");

    section.className =
        "menu-section";


    /* -----------------------------------------------------
       Nadpis + názvy cenových sloupců
       ----------------------------------------------------- */

    const headingRow =
        document.createElement("div");

    headingRow.className =
        "main-dishes-heading";


    const heading =
        document.createElement("h3");

    heading.textContent =
        "Hlavní jídla";


    const priceHeaders =
        document.createElement("div");

    priceHeaders.className =
        "main-dishes-price-headers";


    const singleHeader =
        document.createElement("span");

    singleHeader.textContent =
        "Samostatně";


    const menuHeader =
        document.createElement("span");

    menuHeader.textContent =
        "Menu";


    priceHeaders.appendChild(singleHeader);
    priceHeaders.appendChild(menuHeader);


    headingRow.appendChild(heading);
    headingRow.appendChild(priceHeaders);

    section.appendChild(headingRow);


    /* -----------------------------------------------------
       Tabulka
       ----------------------------------------------------- */

    const table =
        document.createElement("table");


    const tbody =
        document.createElement("tbody");


    for (const dish of dishes) {

        const row =
            document.createElement("tr");


        /* -------------------------------------------------
           Název jídla
           ------------------------------------------------- */

        const nameCell =
            document.createElement("td");


        const name =
            document.createElement("strong");

        name.textContent =
            dish.name;

        nameCell.appendChild(name);


        /* -------------------------------------------------
           Alergeny
           ------------------------------------------------- */

        if (dish.allergens) {

            const allergens =
                document.createElement("div");

            allergens.className =
                "allergens";

            allergens.appendChild(
                createAllergenLinks(
                    dish.allergens
                )
            );

            nameCell.appendChild(allergens);
        }


        /* -------------------------------------------------
           Poznámka
           ------------------------------------------------- */

        if (dish.note) {

            const note =
                document.createElement("div");

            note.className =
                "dish-note";

            note.textContent =
                dish.note;

            nameCell.appendChild(note);
        }


        row.appendChild(nameCell);


        /* -------------------------------------------------
           Cena SAMOSTATNĚ
           ------------------------------------------------- */

        const singlePriceCell =
            document.createElement("td");

        singlePriceCell.className =
            "price";


        if (dish.price_single != null) {

            singlePriceCell.textContent =
                dish.price_single + " Kč";
        }


        row.appendChild(singlePriceCell);


        /* -------------------------------------------------
           Cena MENU
           ------------------------------------------------- */

        const menuPriceCell =
            document.createElement("td");

        menuPriceCell.className =
            "price";


        if (dish.price_menu != null) {

            menuPriceCell.textContent =
                dish.price_menu + " Kč";
        }


        row.appendChild(menuPriceCell);


        tbody.appendChild(row);
    }


    table.appendChild(tbody);

    section.appendChild(table);


    return section;
}


/* =========================================================
   ALERGENY
   ========================================================= */

function createAllergenLinks(allergens) {

    const container =
        document.createDocumentFragment();


    const label =
        document.createElement("span");

    label.className =
        "allergen-label";

    label.textContent =
        "Alergeny: ";

    container.appendChild(label);


    const codes =
        allergens
            .split(",")
            .map(code => code.trim())
            .filter(code => code !== "");


    codes.forEach((code, index) => {

        const wrapper =
            document.createElement("span");

        wrapper.className =
            "allergen";

        wrapper.dataset.code =
            code;


        const codeText =
            document.createElement("span");

        codeText.textContent =
            code;

        wrapper.appendChild(codeText);


        const data =
            allergenData[code];


        if (data) {

            const tooltip =
                document.createElement("span");

            tooltip.className =
                "allergen-tooltip";


            const title =
                document.createElement("strong");

            title.textContent =
                data.title;

            tooltip.appendChild(title);


            const description =
                document.createElement("div");

            description.textContent =
                data.description;

            tooltip.appendChild(description);


            wrapper.appendChild(tooltip);

        } else {

            const tooltip =
                document.createElement("span");

            tooltip.className =
                "allergen-tooltip";


            const title =
                document.createElement("strong");

            title.textContent =
                "Alergen " + code;

            tooltip.appendChild(title);


            const description =
                document.createElement("div");

            description.textContent =
                "Podrobné informace o tomto alergenu nejsou v seznamu uvedeny.";

            tooltip.appendChild(description);


            wrapper.appendChild(tooltip);
        }


        container.appendChild(wrapper);


        if (
            index <
            codes.length - 1
        ) {

            container.appendChild(
                document.createTextNode(" ")
            );
        }
    });


    return container;
}


/* =========================================================
   OVLÁDÁNÍ TOOLTIPŮ
   ========================================================= */

function setupAllergenTooltips() {

    const allergens =
        document.querySelectorAll(
            ".allergen"
        );


    allergens.forEach(allergen => {

        const tooltip =
            allergen.querySelector(
                ".allergen-tooltip"
            );


        if (!tooltip) {
            return;
        }


        allergen.addEventListener(
            "mouseenter",
            () => {

                positionTooltip(
                    allergen,
                    tooltip
                );
            }
        );


        allergen.addEventListener(
            "click",
            event => {

                event.stopPropagation();


                const wasActive =
                    allergen.classList.contains(
                        "active"
                    );


                closeAllAllergens();


                if (!wasActive) {

                    allergen.classList.add(
                        "active"
                    );


                    positionTooltip(
                        allergen,
                        tooltip
                    );
                }
            }
        );
    });


    document.addEventListener(
        "click",
        event => {

            if (
                !event.target.closest(
                    ".allergen"
                )
            ) {

                closeAllAllergens();
            }
        }
    );


    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Escape"
            ) {

                closeAllAllergens();
            }
        }
    );


    window.addEventListener(
        "resize",
        () => {

            const active =
                document.querySelector(
                    ".allergen.active"
                );


            if (!active) {
                return;
            }


            const tooltip =
                active.querySelector(
                    ".allergen-tooltip"
                );


            if (tooltip) {

                positionTooltip(
                    active,
                    tooltip
                );
            }
        }
    );
}


/* =========================================================
   UMÍSTĚNÍ TOOLTIPU
   ========================================================= */

function positionTooltip(
    allergen,
    tooltip
) {

    tooltip.classList.remove(
        "tooltip-right"
    );


    tooltip.style.width = "";


    const allergenRect =
        allergen.getBoundingClientRect();


    const tooltipWidth =
        tooltip.offsetWidth;


    const viewportWidth =
        window.innerWidth;


    const margin = 10;


    const leftPosition =
        allergenRect.left;


    const rightPosition =
        leftPosition +
        tooltipWidth;


    if (
        rightPosition >
        viewportWidth - margin
    ) {

        tooltip.classList.add(
            "tooltip-right"
        );
    }


    if (
        tooltipWidth >
        viewportWidth - (margin * 2)
    ) {

        tooltip.style.width =
            `calc(100vw - ${margin * 2}px)`;
    }
}


/* =========================================================
   ZAVŘENÍ VŠECH ALERGENŮ
   ========================================================= */

function closeAllAllergens() {

    document
        .querySelectorAll(
            ".allergen.active"
        )
        .forEach(allergen => {

            allergen.classList.remove(
                "active"
            );
        });
}


/* =========================================================
   FORMÁTOVÁNÍ DATA
   ========================================================= */

function formatDate(dateString) {

    if (!dateString) {
        return "";
    }


    const parts =
        dateString.split("-");


    if (
        parts.length !== 3
    ) {

        return dateString;
    }


    const year =
        parts[0];

    const month =
        parts[1];

    const day =
        parts[2];


    return (
        day +
        "." +
        month +
        "." +
        year
    );
}


/* =========================================================
   FORMÁTOVÁNÍ ČASU
   ========================================================= */

function formatDateTime(dateTimeString) {

    if (!dateTimeString) {
        return "";
    }


    const date =
        new Date(dateTimeString);


    if (
        isNaN(
            date.getTime()
        )
    ) {

        return dateTimeString;
    }


    return date.toLocaleString(
        "cs-CZ",
        {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        }
    );
}


/* =========================================================
   SPUŠTĚNÍ
   ========================================================= */

loadMenu();