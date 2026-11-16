// @ts-check
/**
 * The DPC Alert card: the alert and the precipitation of each day of a place,
 * at a glance, in the colors of the DPC maps.
 *
 * A Lovelace card (`custom:dpc-card`), listed in the card picker as soon as the
 * integration is installed: the integration serves this file next to the
 * dashboard strategy, whose helpers it shares, and has the frontend load it
 * (custom_components/dpc/dashboard.py).
 *
 * It draws nothing of its own: it is a card of Home Assistant (`ha-card`) with
 * native cards inside, a heading and a tile for the alert and the precipitation
 * of each day, without their own background, so that the whole place is one
 * card, like a tile with its features, and follows the theme. What it adds is
 * finding the entities of the place, by their translation key and the day of
 * their device, so it keeps working when users rename them, and the colors of
 * their states, which native cards cannot change by state.
 */

import {
  ALERT_COLORS,
  DAYS,
  HIGHEST_ALERT_COLORS,
  HIGHEST_PRECIPITATION_COLORS,
  ICON,
  PRECIPITATION_COLORS,
  findPlaces,
  textsIn,
  tile,
} from "./dpc-dashboard.js";

/**
 * @typedef {import("./dpc-dashboard.js").Hass} Hass
 * @typedef {import("./dpc-dashboard.js").Place} Place
 * @typedef {import("./dpc-dashboard.js").Card} Card
 *
 * @typedef {object} StateObject The state of an entity, as the frontend has it.
 * @property {string} entity_id
 * @property {string} state
 *
 * @typedef {Hass & { states: Record<string, StateObject> }} CardHass
 *   The parts of the Home Assistant object the card reads.
 *
 * @typedef {object} CardConfig
 * @property {string} [device_id] The device of the place; the first place without it.
 *
 * @typedef {object} Swatch An entity and the color of its state.
 * @property {string} entity
 * @property {string | undefined} color None without data or for an unknown state.
 *
 * @typedef {object} DayModel What the card shows of a day.
 * @property {string} day e.g. "today"
 * @property {string} name The name of the day, as its device says it.
 * @property {Swatch | undefined} alert None for the day after tomorrow,
 *   which only the vigilance bulletin covers.
 * @property {Swatch | undefined} precipitation
 *
 * @typedef {object} CardModel What the card shows of a place.
 * @property {string} name
 * @property {Swatch | undefined} highestAlert
 * @property {Swatch | undefined} highestPrecipitation
 * @property {DayModel[]} days
 *
 * @typedef {object} Layout The native cards inside the card.
 * @property {Card | undefined} heading
 * @property {Card[][]} rows The cards of each row: the alert and the
 *   precipitation of a day, or a single card, as wide as the row.
 */

/** The name of the card, `custom:dpc-card` in a dashboard. */
export const CARD = "dpc-card";

/**
 * Return the place a card shows: the place of its device, or the first place.
 *
 * @param {Place[]} places
 * @param {CardConfig} config
 */
export function placeOf(places, config) {
  return config.device_id
    ? places.find((place) => place.device.id === config.device_id)
    : places[0];
}

/**
 * Return an entity and the color of its state; none without the entity.
 *
 * @param {Record<string, StateObject>} states
 * @param {string | undefined} entity
 * @param {Record<string, string>} colors The color of each state.
 * @returns {Swatch | undefined}
 */
export function swatch(states, entity, colors) {
  if (!entity) {
    return undefined;
  }
  const state = states[entity]?.state;
  return { entity, color: state === undefined ? undefined : colors[state] };
}

/**
 * Return what the card shows of a place: its highest alert and precipitation,
 * and the alert and the precipitation of each of its days.
 *
 * @param {Place} place
 * @param {Record<string, StateObject>} states
 * @returns {CardModel}
 */
export function cardModel(place, states) {
  return {
    name: place.name,
    highestAlert: swatch(states, place.entity("sensor", "highest_alert"), HIGHEST_ALERT_COLORS),
    highestPrecipitation: swatch(
      states,
      place.entity("sensor", "highest_precipitation"),
      HIGHEST_PRECIPITATION_COLORS,
    ),
    days: DAYS.filter((day) => place.days.has(day)).map((day) => ({
      day,
      name: place.dayName(day),
      alert: swatch(states, place.entity("sensor", "alert", day), ALERT_COLORS),
      precipitation: swatch(
        states,
        place.entity("sensor", "precipitation", day),
        PRECIPITATION_COLORS,
      ),
    })),
  };
}

/**
 * Return the color option of a card: the color of the state, if it has one.
 *
 * @param {Swatch} item
 */
function colorOf(item) {
  return item.color ? { color: item.color } : {};
}

/**
 * Return the badge of the heading for an entity of the place, in its color.
 *
 * @param {Swatch | undefined} item
 * @returns {Card[]}
 */
function badge(item) {
  return item ? [{ type: "entity", entity: item.entity, ...colorOf(item) }] : [];
}

/**
 * Return the row of a day: its alert, named after the day, and its
 * precipitation; without an alert, its precipitation, named after the day.
 *
 * @param {Hass} hass
 * @param {DayModel} day
 * @returns {Card[]}
 */
function dayRow(hass, day) {
  const main = day.alert ?? day.precipitation;
  /** @type {Card[]} */
  const cards = main
    ? [{ type: "tile", entity: main.entity, name: day.name, ...colorOf(main) }]
    : [];
  if (day.alert && day.precipitation) {
    cards.push(tile(hass, day.precipitation.entity, colorOf(day.precipitation)));
  }
  return cards;
}

/**
 * Return the native cards that show a place: a heading with its highest alert
 * and precipitation, and a row for each day.
 *
 * @param {Hass} hass
 * @param {CardModel} model
 * @returns {Layout}
 */
export function placeLayout(hass, model) {
  return {
    heading: {
      type: "heading",
      heading: model.name,
      icon: ICON,
      badges: [...badge(model.highestAlert), ...badge(model.highestPrecipitation)],
    },
    rows: model.days.map((day) => dayRow(hass, day)).filter((row) => row.length),
  };
}

/**
 * Return the native cards a card shows: its place, or a message without one.
 *
 * @param {CardHass} hass
 * @param {Place[]} places
 * @param {CardConfig} config
 * @returns {Layout}
 */
export function cardLayout(hass, places, config) {
  const place = placeOf(places, config);
  if (!place) {
    const texts = textsIn(hass.locale?.language ?? hass.language);
    return { heading: undefined, rows: [[{ type: "markdown", content: texts.no_places }]] };
  }
  return placeLayout(hass, cardModel(place, hass.states));
}

/**
 * The style of the card. The native cards inside lose their own background,
 * border and shadow, so that the card is one surface, as the theme draws it.
 * The alert of a day is narrower than its precipitation, whose texts are longer.
 */
const STYLE = `
  ha-card {
    overflow: hidden;
  }
  /* Inside the card, which keeps its own surface */
  .content {
    --ha-card-background: transparent;
    --ha-card-border-width: 0px;
    --ha-card-box-shadow: none;
  }
  .rows {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
    padding-block-end: 4px;
  }
  .wide {
    grid-column: 1 / -1;
  }
`;

if (globalThis.customElements && globalThis.HTMLElement) {
  class DpcCard extends HTMLElement {
    /** @type {CardConfig} */
    #config = {};

    /** @type {CardHass | undefined} */
    #hass;

    /** The places, found again only when the registries change. */
    /** @type {{ entities: unknown, devices: unknown, places: Place[] } | undefined} */
    #places;

    /** The native cards inside, and the layout they were created from. */
    /** @type {any[]} */
    #cards = [];

    #shown = "";

    /** @type {number} */
    #size = 1;

    constructor() {
      super();
      this.attachShadow({ mode: "open" });
    }

    /** @param {CardConfig} config */
    setConfig(config) {
      if (config.device_id !== undefined && typeof config.device_id !== "string") {
        throw new Error("device_id must be the ID of the device of a DPC place");
      }
      this.#config = config;
      this.#update();
    }

    /** @param {CardHass} hass */
    set hass(hass) {
      this.#hass = hass;
      this.#update();
    }

    getCardSize() {
      return this.#size;
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6 };
    }

    /** @param {CardHass} hass */
    static getStubConfig(hass) {
      const place = findPlaces(hass)[0];
      return place ? { device_id: place.device.id } : {};
    }

    /** Return the places, from the registries of the last time they changed. */
    #findPlaces() {
      const hass = /** @type {CardHass} */ (this.#hass);
      if (this.#places?.entities !== hass.entities || this.#places?.devices !== hass.devices) {
        this.#places = {
          entities: hass.entities,
          devices: hass.devices,
          places: findPlaces(hass),
        };
      }
      return this.#places.places;
    }

    /**
     * Create the native cards again when what they show changes, such as the
     * color of a state; otherwise only give them the new states.
     */
    async #update() {
      const hass = this.#hass;
      if (!hass || !this.shadowRoot) {
        return;
      }
      const layout = cardLayout(hass, this.#findPlaces(), this.#config);
      const shown = JSON.stringify(layout);
      if (shown !== this.#shown) {
        this.#shown = shown;
        const helpers = await /** @type {any} */ (window).loadCardHelpers();
        // A newer update may have created its cards while the helpers loaded
        if (shown !== this.#shown) {
          return;
        }
        this.#render(layout, helpers.createCardElement);
      }
      for (const card of this.#cards) {
        card.hass = this.#hass;
      }
    }

    /**
     * Put the native cards of a layout in the card.
     *
     * @param {Layout} layout
     * @param {(config: Card) => any} createCardElement
     */
    #render(layout, createCardElement) {
      const root = /** @type {ShadowRoot} */ (this.shadowRoot);
      const style = document.createElement("style");
      style.textContent = STYLE;
      const card = document.createElement("ha-card");
      const content = document.createElement("div");
      content.className = "content";
      const rows = document.createElement("div");
      rows.className = "rows";
      this.#cards = [];
      if (layout.heading) {
        const heading = createCardElement(layout.heading);
        this.#cards.push(heading);
        content.append(heading);
      }
      for (const row of layout.rows) {
        for (const config of row) {
          const element = createCardElement(config);
          if (row.length === 1) {
            element.classList.add("wide");
          }
          this.#cards.push(element);
          rows.append(element);
        }
      }
      content.append(rows);
      card.append(content);
      root.replaceChildren(style, card);
      this.#size = 1 + layout.rows.length;
    }
  }

  customElements.get(CARD) || customElements.define(CARD, DpcCard);

  // Listed in the card picker, with a preview
  const cards = /** @type {any} */ (window).customCards ?? [];
  /** @type {any} */ (window).customCards = cards;
  if (!cards.some((/** @type {{ type: string }} */ item) => item.type === CARD)) {
    cards.push({
      type: CARD,
      name: "DPC Alert",
      description: textsIn(document.documentElement.lang || navigator.language).description,
      preview: true,
      documentationURL:
        "https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert#card",
    });
  }
}
