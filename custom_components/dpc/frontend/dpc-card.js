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
 * Each has a visual editor: the place, the title, the highest levels, the days
 * or the data of the bulletins, and one or two columns.
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
  PRECIPITATION_COLORS,
  dayName,
  findPlaces,
  textsIn,
  tile,
  translated,
  withTexts,
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
 *   The parts of the Home Assistant object the cards read.
 *
 * @typedef {object} CardConfig What a card shows; without an option, all of it.
 * @property {string} [type]
 * @property {string} [device_id] The device of the place; the first place without it.
 * @property {boolean} [show_title] The name of the place, above the rest.
 * @property {boolean} [show_highest_alert] The highest alert of the place, in the heading.
 * @property {boolean} [show_highest_precipitation] Its highest precipitation, in the heading.
 * @property {string[]} [days] The days shown, of those the place has.
 * @property {string[]} [items] The data of the bulletins the bulletin card shows.
 * @property {number} [columns] 1, or 2 side by side.
 * @property {boolean} [show_zone] The zone of the map, beside it.
 * @property {boolean} [show_nearby_phenomena] The number of phenomena near the
 *   place on the day of the map, beside it.
 * @property {MapKind} [map] The map of the map card.
 *
 * @typedef {"criticality" | "vigilance"} MapKind
 *
 * @typedef {object} Swatch An entity and the color of its state.
 * @property {string} entity
 * @property {string | undefined} color None without data, or for an unknown state.
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
 *
 * @typedef {Record<string, any>} FormField A field of the visual editor, as
 *   `ha-form` draws it, with its label.
 */

/** The name of the alert card, `custom:dpc-card` in a dashboard. */
export const CARD = "dpc-card";

/** The name of the bulletin card, `custom:dpc-bulletin-card` in a dashboard. */
export const BULLETIN_CARD = "dpc-bulletin-card";

/** The name of the map card, `custom:dpc-map-card` in a dashboard. */
export const MAP_CARD = "dpc-map-card";

/** The days DPC publishes maps of: none of the day after tomorrow. */
export const MAP_DAYS = ["today", "tomorrow"];

/**
 * The maps of the map card: the image of each day, the zone of the place, the
 * sensor of the day its block shows, and the sensor of the place its heading
 * shows, with their colors and the option that shows it.
 */
export const MAPS = {
  criticality: {
    image: "criticality_map",
    zone: "alert_zone",
    day: "alert",
    dayColors: ALERT_COLORS,
    place: "highest_alert",
    placeColors: HIGHEST_ALERT_COLORS,
    placeOption: "show_highest_alert",
  },
  vigilance: {
    image: "vigilance_map",
    zone: "vigilance_zone",
    day: "precipitation",
    dayColors: PRECIPITATION_COLORS,
    place: "highest_precipitation",
    placeColors: HIGHEST_PRECIPITATION_COLORS,
    placeOption: "show_highest_precipitation",
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
 * The data of the bulletins, those of the criticality bulletin first: the
 * order of a single column, and of the editor.
 */
export const BULLETIN_ITEMS = [0, 1].flatMap((column) => BULLETIN_ROWS.map((row) => row[column]));

/** The width of each column of two: the alert of a day is narrower than its
 * precipitation, whose texts are longer. */
const ALERT_COLUMNS = "minmax(0, 2fr) minmax(0, 3fr)";
const EVEN_COLUMNS = "minmax(0, 1fr) minmax(0, 1fr)";
const ONE_COLUMN = "minmax(0, 1fr)";

/**
 * Return the options of a card that show everything: what it shows without them.
 *
 * @param {string} type
 */
export function defaultsOf(type) {
  return {
    show_title: true,
    show_highest_alert: true,
    show_highest_precipitation: true,
    days: type === MAP_CARD ? MAP_DAYS : DAYS,
    items: BULLETIN_ITEMS,
    columns: 2,
    map: "criticality",
    show_zone: true,
    show_nearby_phenomena: true,
  };
}

/**
 * Return the options of the heading of a card, which its editor lists, each
 * with the option of the configuration it sets: the highest level of the map
 * card is that of its map, so that it stays checked when the map changes.
 *
 * @param {string} type
 * @param {MapKind} [map]
 * @returns {Record<string, keyof CardConfig>}
 */
export function headingOptions(type, map = "criticality") {
  if (type === BULLETIN_CARD) {
    return { show_title: "show_title" };
  }
  if (type === MAP_CARD) {
    return {
      show_title: "show_title",
      show_highest: /** @type {keyof CardConfig} */ (MAPS[map].placeOption),
    };
  }
  return {
    show_title: "show_title",
    show_highest_alert: "show_highest_alert",
    show_highest_precipitation: "show_highest_precipitation",
  };
}

/**
 * Return the details beside the map of the map card, which its editor lists,
 * each with the option of the configuration it sets.
 *
 * @param {string} type
 * @returns {Record<string, keyof CardConfig>}
 */
export function detailsOptions(type) {
  return type === MAP_CARD
    ? { show_zone: "show_zone", show_nearby_phenomena: "show_nearby_phenomena" }
    : {};
}

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
 * Return the color option of a card: the color of the state, if it has one.
 *
 * @param {Swatch} item
 */
function colorOf(item) {
  return item.color ? { color: item.color } : {};
}

/**
 * Return the heading of a card: the place, with badges of its entities, each
 * in the color of its state. Without the title, only the badges; without
 * either, no heading.
 *
 * @param {CardConfig} config
 * @param {string} name
 * @param {Array<Swatch | undefined | false>} badges
 * @returns {Placed[]}
 */
function heading(config, name, badges) {
  const shown = badges.flatMap((item) =>
    item ? [{ type: "entity", entity: item.entity, ...colorOf(item) }] : [],
  );
  const title = config.show_title ?? true;
  if (!title && !shown.length) {
    return [];
  }
  return [
    {
      card: {
        type: "heading",
        heading: title ? name : "",
        ...(title ? { icon: ICON } : {}),
        badges: shown,
      },
      column: "all",
    },
  ];
}

/**
 * Return what the alert card shows of a place: its highest alert and
 * precipitation, and the alert and the precipitation of each of its days.
 *
 * @param {CardHass} hass
 * @param {Place} place
 * @param {string[]} [days] The days chosen; all of them without a choice.
 * @returns {CardModel}
 */
export function cardModel(hass, place, days = DAYS) {
  const { states } = hass;
  return {
    name: place.name,
    highestAlert: swatch(states, place.entity("sensor", "highest_alert"), HIGHEST_ALERT_COLORS),
    highestPrecipitation: swatch(
      states,
      place.entity("sensor", "highest_precipitation"),
      HIGHEST_PRECIPITATION_COLORS,
    ),
    days: DAYS.filter((day) => place.days.has(day) && days.includes(day)).map((day) => ({
      day,
      name: dayName(hass, place, day),
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
 * Return the tiles of a day: its alert, named after the day, and its
 * precipitation, named in the language of the user. Without an alert, the
 * precipitation keeps its column, named after the day. In a single column,
 * one below the other.
 *
 * @param {CardHass} hass
 * @param {DayModel} day
 * @param {boolean} single Whether the card has a single column.
 * @returns {Placed[]}
 */
function dayTiles(hass, day, single) {
  const { alert, precipitation } = day;
  /** @type {Placed[]} */
  const tiles = [];
  if (alert) {
    tiles.push({
      card: { type: "tile", entity: alert.entity, name: day.name, ...colorOf(alert) },
      column: single ? "all" : "start",
    });
  }
  if (precipitation) {
    const options = colorOf(precipitation);
    tiles.push({
      card: alert
        ? tile(hass, precipitation.entity, options)
        : { type: "tile", entity: precipitation.entity, name: day.name, ...options },
      column: single ? "all" : "end",
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
 * @param {CardConfig} [config]
 * @returns {Placed[]}
 */
export function placeLayout(hass, model, config = {}) {
  return [
    ...heading(config, model.name, [
      (config.show_highest_alert ?? true) && model.highestAlert,
      (config.show_highest_precipitation ?? true) && model.highestPrecipitation,
    ]),
    ...model.days.flatMap((day) => dayTiles(hass, day, config.columns === 1)),
  ];
}

/** @type {PlaceLayout} */
export function alertLayout(hass, place, config) {
  return placeLayout(hass, cardModel(hass, place, config.days), config);
}

/**
 * Return the native cards of the bulletin card: a heading with the place, and
 * the zone, the publication and the validity of the criticality bulletin, and
 * beside them those of the vigilance bulletin; in a single column, those of
 * the criticality bulletin first. Only the data chosen, as the place has it.
 *
 * @type {PlaceLayout}
 */
export function bulletinLayout(hass, place, config) {
  const chosen = config.items ?? BULLETIN_ITEMS;
  /** @param {string} key @param {Column} column @returns {Placed[]} */
  const placed = (key, column) => {
    const entity = chosen.includes(key) ? place.entity("sensor", key) : undefined;
    return entity ? [{ card: tile(hass, entity), column }] : [];
  };
  const items =
    config.columns === 1
      ? BULLETIN_ITEMS.flatMap((key) => placed(key, "all"))
      : // A row with only the vigilance datum keeps it in its column
        BULLETIN_ROWS.flatMap(([criticality, vigilance]) => [
          ...placed(criticality, "start"),
          ...placed(vigilance, "end"),
        ]);
  return [...heading(config, place.name, []), ...items];
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
 * Return the list of the map card: a block for each day, its alert, or its
 * precipitation for the vigilance map; the zone of the map; and the number of
 * phenomena near the place on a day.
 *
 * @param {CardHass} hass
 * @param {Place} place
 * @param {CardConfig} config
 * @param {string[]} days
 * @param {{ shown?: string, switches: boolean, column: Column }} how The day of
 *   the phenomena, whether a click on a block shows its map, and the column.
 * @returns {Placed[]}
 */
function mapList(hass, place, config, days, { shown, switches, column }) {
  const kind = MAPS[config.map ?? "criticality"];
  /** @type {Placed[]} */
  const list = days.flatMap((day) => {
    const block = swatch(hass.states, place.entity("sensor", kind.day, day), kind.dayColors);
    if (!block) {
      return [];
    }
    const name = dayName(hass, place, day);
    return switches
      ? [
          {
            card: {
              type: "tile",
              entity: block.entity,
              name,
              // The block shows its map; the card handles the click
              tap_action: { action: "none" },
              icon_tap_action: { action: "none" },
              ...colorOf(block),
            },
            column,
            select: day,
            selected: day === shown,
          },
        ]
      : [{ card: { type: "tile", entity: block.entity, name, ...colorOf(block) }, column }];
  });
  const details = [
    (config.show_zone ?? true) && place.entity("sensor", kind.zone),
    (config.show_nearby_phenomena ?? true) &&
      shown !== undefined &&
      place.entity("sensor", "nearby_phenomena", shown),
  ];
  for (const entity of details) {
    if (entity) {
      list.push({ card: tile(hass, entity), column });
    }
  }
  return list;
}

/**
 * Return the native cards of the map card: a heading with the place and its
 * highest level, the map of the selected day (the first without one), and
 * beside it, as high as the map, a list: a block for each day chosen with a
 * map, the zone of the map, and the number of phenomena near the place on the
 * day of the map.
 *
 * With more than one day, a click on a block shows its map, and the block of
 * the map shown stands out. A single day is a tile like the others, which
 * shows its details.
 *
 * Without a map, the list takes the whole card, with the days that have data:
 * DPC often publishes the maps blank, and has none of tomorrow from midnight
 * until its next bulletin.
 *
 * @type {PlaceLayout}
 */
export function mapLayout(hass, place, config, selected) {
  const kind = MAPS[config.map ?? "criticality"];
  const chosen = MAP_DAYS.filter((day) => (config.days ?? MAP_DAYS).includes(day));
  const days = chosen.filter((day) => hasData(hass, place.entity("image", kind.image, day)));
  const shown = selected && days.includes(selected) ? selected : days[0];
  const highest = swatch(hass.states, place.entity("sensor", kind.place), kind.placeColors);
  /** @type {Placed[]} */
  const layout = heading(config, place.name, [
    (config[/** @type {keyof CardConfig} */ (kind.placeOption)] ?? true) && highest,
  ]);
  if (!shown) {
    const withData = chosen.filter((day) => hasData(hass, place.entity("sensor", kind.day, day)));
    return [
      ...layout,
      ...mapList(hass, place, config, withData, {
        shown: withData[0],
        switches: false,
        column: "all",
      }),
    ];
  }
  const beside = mapList(hass, place, config, days, {
    shown,
    switches: days.length > 1,
    column: "end",
  });
  layout.push(
    {
      card: {
        type: "picture-entity",
        entity: /** @type {string} */ (place.entity("image", kind.image, shown)),
        show_name: false,
        show_state: false,
      },
      column: "start",
      rows: Math.max(beside.length, 1),
    },
    ...beside,
  );
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
 * Check that an option is a list of some of the values it accepts.
 *
 * @param {CardConfig} config
 * @param {"days" | "items"} option
 * @param {string[]} values
 */
function checkList(config, option, values) {
  const list = config[option];
  if (
    list !== undefined &&
    !(Array.isArray(list) && list.every((value) => values.includes(value)))
  ) {
    throw new Error(`${option} must be a list of: ${values.join(", ")}`);
  }
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
  for (const option of /** @type {const} */ ([
    "show_title",
    "show_highest_alert",
    "show_highest_precipitation",
    "show_zone",
    "show_nearby_phenomena",
  ])) {
    if (config[option] !== undefined && typeof config[option] !== "boolean") {
      throw new Error(`${option} must be true or false`);
    }
  }
  checkList(config, "days", DAYS);
  checkList(config, "items", BULLETIN_ITEMS);
  if (config.columns !== undefined && config.columns !== 1 && config.columns !== 2) {
    throw new Error("columns must be 1 or 2");
  }
}

/**
 * Return whether two values of an option are the same: lists whatever their order.
 *
 * @param {unknown} value
 * @param {unknown} other
 */
function same(value, other) {
  if (Array.isArray(value) && Array.isArray(other)) {
    return value.length === other.length && value.every((item) => other.includes(item));
  }
  return value === other;
}

/**
 * Return the configuration of a card from its visual editor: the columns as a
 * number, the lists of the heading and the details as their options, the
 * other lists in their order,
 * and without the options that show what the card shows anyway, so that its
 * YAML stays short.
 *
 * @param {string} type
 * @param {Record<string, any>} value
 * @returns {CardConfig}
 */
export function cleanConfig(type, value) {
  /** @type {Record<string, any>} */
  const config = { ...value };
  if (typeof config.columns === "string") {
    config.columns = Number(config.columns);
  }
  const lists = { heading: headingOptions(type, config.map), details: detailsOptions(type) };
  for (const [field, options] of Object.entries(lists)) {
    if (Array.isArray(config[field])) {
      for (const [option, key] of Object.entries(options)) {
        config[key] = config[field].includes(option);
      }
      delete config[field];
    }
  }
  if (Array.isArray(config.days)) {
    config.days = DAYS.filter((day) => config.days.includes(day));
  }
  if (Array.isArray(config.items)) {
    config.items = BULLETIN_ITEMS.filter((item) => config.items.includes(item));
  }
  for (const [option, fallback] of Object.entries(defaultsOf(type))) {
    if (same(config[option], fallback)) {
      delete config[option];
    }
  }
  return config;
}

/**
 * Return the data of the visual editor of a card: its options, with those it
 * leaves out as they show, the place it shows, and what its heading and the
 * details beside its map show.
 *
 * @param {string} type
 * @param {Place[]} places
 * @param {CardConfig} config
 */
export function editorData(type, places, config) {
  const defaults = defaultsOf(type);
  /** @type {Record<string, any>} */
  const options = { ...defaults, ...config };
  return {
    ...options,
    device_id: config.device_id ?? places[0]?.device.id,
    heading: Object.entries(headingOptions(type, config.map))
      .filter(([, key]) => options[key])
      .map(([option]) => option),
    details: Object.entries(detailsOptions(type))
      .filter(([, key]) => options[key])
      .map(([option]) => option),
    columns: String(config.columns ?? defaults.columns),
  };
}

/**
 * Return the name of a day as the integration names it in the language of
 * the user: "Hoje", without the place.
 *
 * @param {Hass} hass
 * @param {string} day
 */
function dayText(hass, day) {
  return translated(hass, `device.${day}.name`, { place: "" })?.replace(/^[\s·]+/, "") || day;
}

/**
 * Return the name of an entity of the integration, by its translation key, in
 * the language of the user.
 *
 * @param {Hass} hass
 * @param {string} domain
 * @param {string} key
 */
function entityText(hass, domain, key) {
  return translated(hass, `entity.${domain}.${key}.name`) || key;
}

/**
 * Return the fields of the visual editor of a card, labeled in the language of
 * the user, with the names of the integration where it has them.
 *
 * @param {string} type
 * @param {Hass} hass
 * @param {Place[]} places
 * @param {CardConfig} config
 * @returns {FormField[]}
 */
export function editorSchema(type, hass, places, config) {
  const texts = textsIn(hass.locale?.language ?? hass.language);
  const options = places.map((place) => ({ value: place.device.id, label: place.name }));
  // A place that is gone stays, by its ID, until another is chosen
  if (config.device_id && !options.some(({ value }) => value === config.device_id)) {
    options.push({ value: config.device_id, label: config.device_id });
  }
  /** @type {FormField[]} */
  const fields = [
    {
      name: "device_id",
      label: texts.place,
      selector: { select: { options, mode: "dropdown" } },
    },
  ];
  // A list, as compact as the days, rather than a switch for each
  /** @type {Record<string, string>} */
  const headingLabels = {
    show_title: texts.title,
    show_highest_alert: entityText(hass, "sensor", "highest_alert"),
    show_highest_precipitation: entityText(hass, "sensor", "highest_precipitation"),
    show_highest: entityText(hass, "sensor", MAPS[config.map ?? "criticality"].place),
  };
  const headingField = {
    name: "heading",
    label: texts.heading,
    selector: {
      select: {
        multiple: true,
        mode: "list",
        options: Object.keys(headingOptions(type, config.map)).map((option) => ({
          value: option,
          label: headingLabels[option],
        })),
      },
    },
  };
  /** @param {string[]} days */
  const daysField = (days) => ({
    name: "days",
    label: texts.days,
    selector: {
      select: {
        multiple: true,
        mode: "list",
        options: days.map((day) => ({ value: day, label: dayText(hass, day) })),
      },
    },
  });
  const columnsField = {
    name: "columns",
    label: texts.columns,
    selector: { select: { options: ["1", "2"], mode: "dropdown" } },
  };
  if (type === MAP_CARD) {
    const kind = MAPS[config.map ?? "criticality"];
    /** @type {Record<string, string>} */
    const detailsLabels = {
      show_zone: entityText(hass, "sensor", kind.zone),
      show_nearby_phenomena: entityText(hass, "sensor", "nearby_phenomena"),
    };
    fields.push(
      {
        name: "map",
        label: texts.maps,
        selector: {
          select: {
            options: Object.entries(MAPS).map(([value, { image }]) => ({
              value,
              label: entityText(hass, "image", image),
            })),
            mode: "dropdown",
          },
        },
      },
      headingField,
      {
        name: "details",
        label: texts.details,
        selector: {
          select: {
            multiple: true,
            mode: "list",
            options: Object.keys(detailsOptions(type)).map((option) => ({
              value: option,
              label: detailsLabels[option],
            })),
          },
        },
      },
      daysField(MAP_DAYS),
    );
  } else if (type === BULLETIN_CARD) {
    fields.push(
      headingField,
      {
        name: "items",
        label: texts.bulletins,
        selector: {
          select: {
            multiple: true,
            mode: "list",
            options: BULLETIN_ITEMS.map((key) => ({
              value: key,
              label: entityText(hass, "sensor", key),
            })),
          },
        },
      },
      columnsField,
    );
  } else {
    fields.push(headingField, daysField(DAYS), columnsField);
  }
  return fields;
}

/**
 * The style of the cards. The native cards inside lose their own background,
 * border and shadow, so that the card is one surface, as the theme draws it;
 * the selected day takes the background the theme gives secondary surfaces.
 *
 * The heading lines up with the tiles: the center of its 18px icon, 4px from
 * its edge, with the center of their 36px icons, 10px from theirs (15px), and
 * its badges, 4px from its edge, with their 10px padding (6px). Without the
 * title, the heading is as wide as its badges, at the start: an empty title
 * and a gap of 8px before them, after its 4px, so their 16px icons line up
 * with those of the tiles (8px).
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
  .badges {
    justify-self: start;
    padding-inline-start: 8px;
    --ha-heading-card-title-min-width: 0px;
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
 * The cards: the layout of each, and the width of its columns.
 *
 * @type {Array<{
 *   type: string,
 *   layout: PlaceLayout,
 *   columns: (config: CardConfig) => string,
 *   name: (texts: ReturnType<typeof textsIn>) => string,
 * }>}
 */
export const CARDS = [
  {
    type: CARD,
    layout: alertLayout,
    columns: (config) => (config.columns === 1 ? ONE_COLUMN : ALERT_COLUMNS),
    name: () => "DPC Alert",
  },
  {
    type: BULLETIN_CARD,
    layout: bulletinLayout,
    columns: (config) => (config.columns === 1 ? ONE_COLUMN : EVEN_COLUMNS),
    name: (texts) => `DPC Alert · ${texts.bulletins}`,
  },
  {
    type: MAP_CARD,
    layout: mapLayout,
    columns: () => EVEN_COLUMNS,
    name: (texts) => `DPC Alert · ${texts.maps}`,
  },
];

if (globalThis.customElements && globalThis.HTMLElement) {
  /**
   * Have the frontend define its forms, which it loads with the editors of
   * its own cards: the editor of a tile has one.
   */
  const loadForms = async () => {
    if (customElements.get("ha-form")) {
      return;
    }
    const helpers = await /** @type {any} */ (window).loadCardHelpers();
    helpers.createCardElement({ type: "tile", entity: "sun.sun" });
    await customElements.whenDefined("hui-tile-card");
    await /** @type {any} */ (customElements.get("hui-tile-card")).getConfigElement();
  };

  /**
   * Return the texts of the frontend with those of the integration in the
   * language of the user, loaded once per language, then a call back.
   */
  class Texts {
    /** @type {string | undefined} */
    #language;

    /** @type {Hass["localize"]} */
    #localize;

    /**
     * Return Home Assistant with the texts loaded so far, and load them in
     * a new language, calling back once they are.
     *
     * @template {Hass} H
     * @param {H} hass
     * @param {() => void} loaded
     * @returns {H}
     */
    of(hass, loaded) {
      const language = hass.locale?.language ?? hass.language;
      if (language !== this.#language) {
        this.#language = language;
        withTexts(hass).then(({ localize }) => {
          this.#localize = localize;
          loaded();
        });
      }
      return { ...hass, localize: this.#localize ?? hass.localize };
    }
  }

  /**
   * The visual editor of a card: a form of Home Assistant.
   *
   * @param {string} type
   */
  const defineEditor = (type) =>
    class extends HTMLElement {
      /** @type {CardConfig | undefined} */
      #config;

      /** @type {Hass | undefined} */
      #hass;

      /** @type {any} */
      #form;

      #texts = new Texts();

      /** @param {CardConfig} config */
      setConfig(config) {
        this.#config = config;
        this.#render();
      }

      /** @param {Hass} hass */
      set hass(hass) {
        this.#hass = hass;
        this.#render();
      }

      #render() {
        if (!this.#hass || !this.#config) {
          return;
        }
        const hass = this.#texts.of(this.#hass, () => this.#render());
        if (!this.#form) {
          this.#form = document.createElement("ha-form");
          this.#form.computeLabel = (/** @type {FormField} */ field) => field.label ?? field.name;
          this.#form.addEventListener("value-changed", (/** @type {CustomEvent} */ event) => {
            event.stopPropagation();
            this.dispatchEvent(
              new CustomEvent("config-changed", {
                detail: { config: cleanConfig(type, event.detail.value) },
                bubbles: true,
                composed: true,
              }),
            );
          });
          this.append(this.#form);
        }
        const places = findPlaces(hass);
        this.#form.hass = this.#hass;
        this.#form.schema = editorSchema(type, hass, places, this.#config);
        this.#form.data = editorData(type, places, this.#config);
      }
    };

  /**
   * A card of a place, made of native cards in one or two columns.
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

      #texts = new Texts();

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

      static async getConfigElement() {
        await loadForms();
        return document.createElement(`${type}-editor`);
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
        if (!this.#hass || !this.shadowRoot) {
          return;
        }
        const hass = this.#texts.of(this.#hass, () => this.#update());
        const placed = cardLayout(layout, hass, this.#findPlaces(), this.#config, this.#selected);
        const shown = JSON.stringify([columns(this.#config), placed]);
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
        content.style.setProperty("--dpc-columns", columns(this.#config));
        this.#cards = placed.map(({ card: config, column, rows, select, selected }) => {
          const element = createCardElement(config);
          element.classList.add(column);
          if (config.type === "heading") {
            element.classList.add(config.heading ? "heading" : "badges");
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
        this.#size = 1 + Math.ceil(placed.length / 2);
      }
    };

  const texts = textsIn(document.documentElement.lang || navigator.language);
  const pickable = /** @type {any} */ (window).customCards ?? [];
  /** @type {any} */ (window).customCards = pickable;
  for (const definition of CARDS) {
    customElements.get(definition.type) ||
      customElements.define(definition.type, defineCard(definition));
    customElements.get(`${definition.type}-editor`) ||
      customElements.define(`${definition.type}-editor`, defineEditor(definition.type));
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
