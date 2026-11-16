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
 * their device, so it keeps working when users rename them; the colors of
 * their states, which native cards cannot change by state; and names in the
 * language of the user, rather than in the language of the server.
 */

import {
  ALERT_COLORS,
  DAYS,
  HIGHEST_ALERT_COLORS,
  HIGHEST_PRECIPITATION_COLORS,
  ICON,
  PLATFORM,
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
 * @typedef {Hass & {
 *   states: Record<string, StateObject>,
 *   localize?: (key: string, values?: Record<string, string>) => string,
 *   loadBackendTranslation?: (category: string, integration: string) => Promise<unknown>,
 * }} CardHass The parts of the Home Assistant object the card reads.
 *
 * @typedef {object} CardConfig
 * @property {string} [device_id] The device of the place; the first place without it.
 *
 * @typedef {object} Swatch An entity and the color of its state.
 * @property {string} entity
 * @property {string | undefined} color None without data, for an unknown
 *   state, or for a state the theme colors better.
 *
 * @typedef {object} DayModel What the card shows of a day.
 * @property {string} day e.g. "today"
 * @property {string} name The name of the day, in the language of the user.
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
 * @typedef {"all" | "alert" | "precipitation"} Column Where a card goes: the
 *   whole width, the column of the alerts, or the wider one of the precipitation.
 *
 * @typedef {object} Placed A native card, and where it goes in the card.
 * @property {Card} card
 * @property {Column} column
 */

/** The name of the card, `custom:dpc-card` in a dashboard. */
export const CARD = "dpc-card";

/**
 * Return the colors of states without white: the DPC maps draw no
 * precipitation in white, which a light theme does not show, so those states
 * keep the color of the theme.
 *
 * @param {Record<string, string>} colors
 */
function withoutWhite(colors) {
  return Object.fromEntries(
    Object.entries(colors).filter(([, color]) => color.toUpperCase() !== "#FFFFFF"),
  );
}

/** Color of each state of the precipitation of a day, on a card. */
const DAY_PRECIPITATION_COLORS = withoutWhite(PRECIPITATION_COLORS);

/** Color of each state of the highest precipitation of a place, on a card. */
const PLACE_PRECIPITATION_COLORS = withoutWhite(HIGHEST_PRECIPITATION_COLORS);

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
 * Return a text of the integration in the language of the user, if the
 * frontend has it.
 *
 * @param {CardHass} hass
 * @param {string} key e.g. "entity.sensor.precipitation.name"
 * @param {Record<string, string>} [values]
 */
export function translated(hass, key, values) {
  return hass.localize?.(`component.${PLATFORM}.${key}`, values) || undefined;
}

/**
 * Return the name of a day of a place in the language of the user: the name
 * the user gave its device, or the name of the days of the integration
 * ("Hoje"), or else the name of its device, in the language of the server.
 *
 * @param {CardHass} hass
 * @param {Place} place
 * @param {string} day
 */
export function dayName(hass, place, day) {
  if (place.days.get(day)?.name_by_user) {
    return place.dayName(day);
  }
  const name = translated(hass, `device.${day}.name`, { place: place.name });
  const prefix = `${place.name} · `;
  if (!name) {
    return place.dayName(day);
  }
  return name.startsWith(prefix) ? name.slice(prefix.length) : name;
}

/**
 * Return what the card shows of a place: its highest alert and precipitation,
 * and the alert and the precipitation of each of its days.
 *
 * @param {CardHass} hass
 * @param {Place} place
 * @returns {CardModel}
 */
export function cardModel(hass, place) {
  const { states } = hass;
  return {
    name: place.name,
    highestAlert: swatch(states, place.entity("sensor", "highest_alert"), HIGHEST_ALERT_COLORS),
    highestPrecipitation: swatch(
      states,
      place.entity("sensor", "highest_precipitation"),
      PLACE_PRECIPITATION_COLORS,
    ),
    days: DAYS.filter((day) => place.days.has(day)).map((day) => ({
      day,
      name: dayName(hass, place, day),
      alert: swatch(states, place.entity("sensor", "alert", day), ALERT_COLORS),
      precipitation: swatch(
        states,
        place.entity("sensor", "precipitation", day),
        DAY_PRECIPITATION_COLORS,
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
 * Return the tiles of a day: its alert, named after the day, and its
 * precipitation, named in the language of the user. Without an alert, the
 * precipitation keeps its column, named after the day.
 *
 * @param {CardHass} hass
 * @param {DayModel} day
 * @returns {Placed[]}
 */
function dayTiles(hass, day) {
  const { alert, precipitation } = day;
  /** @type {Placed[]} */
  const tiles = [];
  if (alert) {
    tiles.push({
      card: { type: "tile", entity: alert.entity, name: day.name, ...colorOf(alert) },
      column: "alert",
    });
  }
  if (precipitation) {
    const name = alert ? translated(hass, "entity.sensor.precipitation.name") : day.name;
    const options = colorOf(precipitation);
    tiles.push({
      card: name
        ? { type: "tile", entity: precipitation.entity, name, ...options }
        : tile(hass, precipitation.entity, options),
      column: "precipitation",
    });
  }
  return tiles;
}

/**
 * Return the native cards that show a place: a heading with its highest alert
 * and precipitation, and the tiles of each day.
 *
 * @param {CardHass} hass
 * @param {CardModel} model
 * @returns {Placed[]}
 */
export function placeLayout(hass, model) {
  return [
    {
      card: {
        type: "heading",
        heading: model.name,
        icon: ICON,
        badges: [...badge(model.highestAlert), ...badge(model.highestPrecipitation)],
      },
      column: "all",
    },
    ...model.days.flatMap((day) => dayTiles(hass, day)),
  ];
}

/**
 * Return the native cards a card shows: its place, or a message without one.
 *
 * @param {CardHass} hass
 * @param {Place[]} places
 * @param {CardConfig} config
 * @returns {Placed[]}
 */
export function cardLayout(hass, places, config) {
  const place = placeOf(places, config);
  if (!place) {
    const texts = textsIn(hass.locale?.language ?? hass.language);
    return [{ card: { type: "markdown", content: texts.no_places }, column: "all" }];
  }
  return placeLayout(hass, cardModel(hass, place));
}

/**
 * The style of the card. The native cards inside lose their own background,
 * border and shadow, so that the card is one surface, as the theme draws it.
 * The alert of a day is narrower than its precipitation, whose texts are longer.
 *
 * The heading lines up with the tiles: the center of its 18px icon, 4px from
 * its edge, with the center of their 36px icons, 10px from theirs (15px), and
 * its badges, 4px from its edge, with their 10px padding (6px).
 */
const STYLE = `
  ha-card {
    overflow: hidden;
  }
  .content {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
    padding-block-end: 4px;
    --ha-card-background: transparent;
    --ha-card-border-width: 0px;
    --ha-card-box-shadow: none;
  }
  .all {
    grid-column: 1 / -1;
  }
  .alert {
    grid-column: 1;
  }
  .precipitation {
    grid-column: 2;
  }
  .heading {
    padding-inline: 15px 6px;
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

    /** The native cards inside. */
    /** @type {any[]} */
    #cards = [];

    /** The layout the native cards were created from. */
    #shown = "";

    /** The language whose names of the days were asked for. */
    /** @type {string | undefined} */
    #language;

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
      this.#loadTranslations(hass);
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

    /**
     * Have the frontend load the names of the days in the language of the
     * user: it has the names of the entities, not those of the devices. With
     * them, it gives the card a new Home Assistant object, which renders it.
     *
     * @param {CardHass} hass
     */
    #loadTranslations(hass) {
      const language = hass.locale?.language ?? hass.language;
      if (language !== this.#language) {
        this.#language = language;
        hass.loadBackendTranslation?.("device", PLATFORM);
      }
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
     * Put the native cards of a layout in the card, each in its column.
     *
     * @param {Placed[]} layout
     * @param {(config: Card) => any} createCardElement
     */
    #render(layout, createCardElement) {
      const root = /** @type {ShadowRoot} */ (this.shadowRoot);
      const style = document.createElement("style");
      style.textContent = STYLE;
      const card = document.createElement("ha-card");
      const content = document.createElement("div");
      content.className = "content";
      this.#cards = layout.map(({ card: config, column }) => {
        const element = createCardElement(config);
        element.classList.add(column);
        if (config.type === "heading") {
          element.classList.add("heading");
        }
        content.append(element);
        return element;
      });
      card.append(content);
      root.replaceChildren(style, card);
      // About a row for the heading, and one for each day of two tiles
      this.#size = 1 + Math.ceil((layout.length - 1) / 2);
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
