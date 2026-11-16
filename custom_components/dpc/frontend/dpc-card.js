// @ts-check
/**
 * The DPC Alert cards, for the dashboards of the users, listed in the card
 * picker as soon as the integration is installed:
 *
 * - `custom:dpc-card`: the alert and the precipitation of each day of a place;
 * - `custom:dpc-bulletin-card`: the bulletins of a place, criticality and
 *   vigilance side by side: their zones, when they were published, and until
 *   when they cover;
 * - `custom:dpc-map-card`: a map of the bulletins, and a block for each day
 *   that has one, which shows its map.
 *
 * The integration serves this file next to the dashboard strategy, whose
 * helpers it shares, and has the frontend load it (custom_components/dpc/dashboard.py).
 *
 * The cards draw nothing of their own: each is a card of Home Assistant
 * (`ha-card`) with native cards inside, without their own background, so that
 * the whole place is one card, like a tile with its features, and follows the
 * theme. What they add is finding the entities of the place, by their
 * translation key and the day of their device, so they keep working when users
 * rename them; the colors of their states, which native cards cannot change by
 * state; and names in the language of the user, rather than of the server.
 */

import {
  ALERT_COLORS,
  DAYS,
  HIGHEST_ALERT_COLORS,
  HIGHEST_PRECIPITATION_COLORS,
  ICON,
  NO_DATA_STATES,
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
 * }} CardHass The parts of the Home Assistant object the cards read.
 *
 * @typedef {object} CardConfig
 * @property {string} [device_id] The device of the place; the first place without it.
 * @property {MapKind} [map] The map of the map card; the criticality map without it.
 *
 * @typedef {"criticality" | "vigilance"} MapKind
 *
 * @typedef {object} Swatch An entity and the color of its state.
 * @property {string} entity
 * @property {string | undefined} color None without data, for an unknown
 *   state, or for a state the theme colors better.
 *
 * @typedef {object} DayModel What the alert card shows of a day.
 * @property {string} day e.g. "today"
 * @property {string} name The name of the day, in the language of the user.
 * @property {Swatch | undefined} alert None for the day after tomorrow,
 *   which only the vigilance bulletin covers.
 * @property {Swatch | undefined} precipitation
 *
 * @typedef {object} CardModel What the alert card shows of a place.
 * @property {string} name
 * @property {Swatch | undefined} highestAlert
 * @property {Swatch | undefined} highestPrecipitation
 * @property {DayModel[]} days
 *
 * @typedef {"all" | "start" | "end"} Column Where a card goes: the whole
 *   width, or one of the two columns of the card.
 *
 * @typedef {object} Placed A native card, and where it goes in the card.
 * @property {Card} card
 * @property {Column} column
 * @property {number} [rows] The rows it spans, such as a map beside its days.
 * @property {string} [select] The day a click on it selects, such as the
 *   day of a map.
 * @property {boolean} [selected] Whether it is the day selected.
 *
 * @typedef {(hass: CardHass, place: Place, config: CardConfig, selected?: string)
 *   => Placed[]} PlaceLayout The native cards a card shows of a place.
 */

/** The name of the alert card, `custom:dpc-card` in a dashboard. */
export const CARD = "dpc-card";

/** The name of the bulletin card, `custom:dpc-bulletin-card` in a dashboard. */
export const BULLETIN_CARD = "dpc-bulletin-card";

/** The name of the map card, `custom:dpc-map-card` in a dashboard. */
export const MAP_CARD = "dpc-map-card";

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
 * The maps of the map card: the image of each day, the sensor of the day its
 * block shows, and the sensor of the place its heading shows, with their colors.
 */
export const MAPS = {
  criticality: {
    image: "criticality_map",
    day: "alert",
    dayColors: ALERT_COLORS,
    place: "highest_alert",
    placeColors: HIGHEST_ALERT_COLORS,
  },
  vigilance: {
    image: "vigilance_map",
    day: "precipitation",
    dayColors: DAY_PRECIPITATION_COLORS,
    place: "highest_precipitation",
    placeColors: PLACE_PRECIPITATION_COLORS,
  },
};

/**
 * The bulletin card: each row, the same data of the criticality bulletin and
 * of the vigilance bulletin, side by side.
 */
const BULLETIN_ROWS = [
  ["alert_zone", "vigilance_zone"],
  ["criticality_bulletin", "vigilance_bulletin"],
  ["criticality_valid_until", "vigilance_valid_until"],
];

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
 * Return the color option of a card: the color of the state, if it has one.
 *
 * @param {Swatch} item
 */
function colorOf(item) {
  return item.color ? { color: item.color } : {};
}

/**
 * Return a tile named in the language of the user, as the integration names
 * its entity: "Precipitação" for the precipitation of a day.
 *
 * @param {CardHass} hass
 * @param {string} entity
 * @param {string} key The translation key of the entity.
 * @param {Card} [options]
 * @returns {Card}
 */
function namedTile(hass, entity, key, options = {}) {
  const domain = entity.split(".")[0];
  const name = translated(hass, `entity.${domain}.${key}.name`);
  return name ? { type: "tile", entity, name, ...options } : tile(hass, entity, options);
}

/**
 * Return the heading of a card: the place, with badges of its entities, each
 * in the color of its state.
 *
 * @param {string} name
 * @param {Array<Swatch | undefined>} badges
 * @returns {Placed}
 */
function heading(name, badges) {
  return {
    card: {
      type: "heading",
      heading: name,
      icon: ICON,
      badges: badges.flatMap((item) =>
        item ? [{ type: "entity", entity: item.entity, ...colorOf(item) }] : [],
      ),
    },
    column: "all",
  };
}

/**
 * Return what the alert card shows of a place: its highest alert and
 * precipitation, and the alert and the precipitation of each of its days.
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
      column: "start",
    });
  }
  if (precipitation) {
    const options = colorOf(precipitation);
    tiles.push({
      card: alert
        ? namedTile(hass, precipitation.entity, "precipitation", options)
        : { type: "tile", entity: precipitation.entity, name: day.name, ...options },
      column: "end",
    });
  }
  return tiles;
}

/**
 * Return the native cards of the alert card: a heading with the highest alert
 * and precipitation of the place, and the tiles of each day.
 *
 * @param {CardHass} hass
 * @param {CardModel} model
 * @returns {Placed[]}
 */
export function placeLayout(hass, model) {
  return [
    heading(model.name, [model.highestAlert, model.highestPrecipitation]),
    ...model.days.flatMap((day) => dayTiles(hass, day)),
  ];
}

/** @type {PlaceLayout} */
export function alertLayout(hass, place) {
  return placeLayout(hass, cardModel(hass, place));
}

/**
 * Return the native cards of the bulletin card: a heading with the place, and
 * the zone, the publication and the validity of the criticality bulletin, and
 * beside them those of the vigilance bulletin.
 *
 * @type {PlaceLayout}
 */
export function bulletinLayout(hass, place) {
  /** @type {Placed[]} */
  const layout = [heading(place.name, [])];
  for (const [criticality, vigilance] of BULLETIN_ROWS) {
    for (const [key, column] of /** @type {Array<[string, Column]>} */ ([
      [criticality, "start"],
      [vigilance, "end"],
    ])) {
      const entity = place.entity("sensor", key);
      if (entity) {
        layout.push({ card: namedTile(hass, entity, key), column });
      }
    }
  }
  return layout;
}

/**
 * Return whether an entity has data, such as a map, which tomorrow has not
 * after midnight until the next bulletin.
 *
 * @param {CardHass} hass
 * @param {string | undefined} entity
 */
function hasData(hass, entity) {
  const state = entity ? hass.states[entity]?.state : undefined;
  return state !== undefined && !NO_DATA_STATES.includes(state);
}

/**
 * Return the native cards of the map card: a heading with the place and its
 * highest level, the map of the selected day (the first without one), and
 * beside it, as high as the map, a block for each day with a map: its alert,
 * or its precipitation for the vigilance map. A click on a block shows its map.
 *
 * @type {PlaceLayout}
 */
export function mapLayout(hass, place, config, selected) {
  const kind = MAPS[config.map ?? "criticality"];
  const days = DAYS.filter((day) => hasData(hass, place.entity("image", kind.image, day)));
  const shown = selected && days.includes(selected) ? selected : days[0];
  const highest = swatch(hass.states, place.entity("sensor", kind.place), kind.placeColors);
  /** @type {Placed[]} */
  const layout = [heading(place.name, [highest])];
  if (!shown) {
    return layout;
  }
  layout.push({
    card: {
      type: "picture-entity",
      entity: /** @type {string} */ (place.entity("image", kind.image, shown)),
      show_name: false,
      show_state: false,
    },
    column: "start",
    rows: days.length,
  });
  for (const day of days) {
    const block = swatch(hass.states, place.entity("sensor", kind.day, day), kind.dayColors);
    if (block) {
      layout.push({
        card: {
          type: "tile",
          entity: block.entity,
          name: dayName(hass, place, day),
          // The block shows its map; the card handles the click
          tap_action: { action: "none" },
          icon_tap_action: { action: "none" },
          ...colorOf(block),
        },
        column: "end",
        select: day,
        selected: day === shown,
      });
    }
  }
  return layout;
}

/**
 * Return the native cards a card shows: those of its place, or a message
 * without one.
 *
 * @param {PlaceLayout} layout
 * @param {CardHass} hass
 * @param {Place[]} places
 * @param {CardConfig} config
 * @param {string} [selected]
 * @returns {Placed[]}
 */
export function cardLayout(layout, hass, places, config, selected) {
  const place = placeOf(places, config);
  if (!place) {
    const texts = textsIn(hass.locale?.language ?? hass.language);
    return [{ card: { type: "markdown", content: texts.no_places }, column: "all" }];
  }
  return layout(hass, place, config, selected);
}

/**
 * Check the configuration of a card, as Home Assistant shows its errors.
 *
 * @param {CardConfig} config
 */
export function checkConfig(config) {
  if (config.device_id !== undefined && typeof config.device_id !== "string") {
    throw new Error("device_id must be the ID of the device of a DPC place");
  }
  if (config.map !== undefined && !Object.keys(MAPS).includes(config.map)) {
    throw new Error(`map must be one of: ${Object.keys(MAPS).join(", ")}`);
  }
}

/**
 * The style of the cards. The native cards inside lose their own background,
 * border and shadow, so that the card is one surface, as the theme draws it;
 * the selected day takes the background the theme gives secondary surfaces.
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
    grid-template-columns: var(--dpc-columns);
    padding-block-end: 4px;
    --ha-card-background: transparent;
    --ha-card-border-width: 0px;
    --ha-card-box-shadow: none;
  }
  .all {
    grid-column: 1 / -1;
  }
  .start {
    grid-column: 1;
  }
  .end {
    grid-column: 2;
  }
  .heading {
    padding-inline: 15px 6px;
  }
  .picture {
    padding: 4px 10px;
  }
  .select {
    cursor: pointer;
  }
  .selected {
    --ha-card-background: var(--secondary-background-color);
  }
`;

/**
 * The cards: the layout of each, and the width of its two columns. The alert
 * of a day is narrower than its precipitation, whose texts are longer.
 *
 * @type {Array<{
 *   type: string,
 *   layout: PlaceLayout,
 *   columns: string,
 *   name: (texts: ReturnType<typeof textsIn>) => string,
 * }>}
 */
export const CARDS = [
  {
    type: CARD,
    layout: alertLayout,
    columns: "minmax(0, 2fr) minmax(0, 3fr)",
    name: () => "DPC Alert",
  },
  {
    type: BULLETIN_CARD,
    layout: bulletinLayout,
    columns: "minmax(0, 1fr) minmax(0, 1fr)",
    name: (texts) => `DPC Alert · ${texts.bulletins}`,
  },
  {
    type: MAP_CARD,
    layout: mapLayout,
    columns: "minmax(0, 1fr) minmax(0, 1fr)",
    name: (texts) => `DPC Alert · ${texts.maps}`,
  },
];

if (globalThis.customElements && globalThis.HTMLElement) {
  /**
   * A card of a place, made of native cards in two columns.
   *
   * @param {(typeof CARDS)[number]} definition
   */
  const defineCard = ({ type, layout, columns }) =>
    class extends HTMLElement {
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

      /** The day the user selected, such as the day of the map shown. */
      /** @type {string | undefined} */
      #selected;

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
        checkConfig(config);
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
        if (
          this.#places?.entities !== hass.entities ||
          this.#places?.devices !== hass.devices
        ) {
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
        const placed = cardLayout(layout, hass, this.#findPlaces(), this.#config, this.#selected);
        const shown = JSON.stringify(placed);
        if (shown !== this.#shown) {
          this.#shown = shown;
          const helpers = await /** @type {any} */ (window).loadCardHelpers();
          // A newer update may have created its cards while the helpers loaded
          if (shown !== this.#shown) {
            return;
          }
          this.#render(placed, helpers.createCardElement);
        }
        for (const card of this.#cards) {
          card.hass = this.#hass;
        }
      }

      /**
       * Put the native cards of a layout in the card, each in its place.
       *
       * @param {Placed[]} placed
       * @param {(config: Card) => any} createCardElement
       */
      #render(placed, createCardElement) {
        const root = /** @type {ShadowRoot} */ (this.shadowRoot);
        const style = document.createElement("style");
        style.textContent = STYLE;
        const card = document.createElement("ha-card");
        const content = document.createElement("div");
        content.className = "content";
        content.style.setProperty("--dpc-columns", columns);
        this.#cards = placed.map(({ card: config, column, rows, select, selected }) => {
          const element = createCardElement(config);
          element.classList.add(column);
          if (config.type === "heading") {
            element.classList.add("heading");
          }
          if (config.type === "picture-entity") {
            element.classList.add("picture");
          }
          if (rows) {
            element.style.gridRow = `span ${rows}`;
          }
          if (select) {
            element.classList.add("select");
            element.classList.toggle("selected", Boolean(selected));
            element.addEventListener("click", () => {
              this.#selected = select;
              this.#update();
            });
          }
          content.append(element);
          return element;
        });
        card.append(content);
        root.replaceChildren(style, card);
        // About a row for the heading, and one for each pair of cards
        this.#size = 1 + Math.ceil((placed.length - 1) / 2);
      }
    };

  const texts = textsIn(document.documentElement.lang || navigator.language);
  const pickable = /** @type {any} */ (window).customCards ?? [];
  /** @type {any} */ (window).customCards = pickable;
  for (const definition of CARDS) {
    customElements.get(definition.type) ||
      customElements.define(definition.type, defineCard(definition));
    // Listed in the card picker, with a preview
    if (!pickable.some((/** @type {{ type: string }} */ item) => item.type === definition.type)) {
      pickable.push({
        type: definition.type,
        name: definition.name(texts),
        description: texts.description,
        preview: true,
        documentationURL:
          "https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert#cards",
      });
    }
  }
}
