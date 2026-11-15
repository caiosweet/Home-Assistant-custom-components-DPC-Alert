// @ts-check
/**
 * The DPC Alert dashboard: the alerts and the weather vigilance of every place
 * of the DPC Alert integration, built from the native cards of Home Assistant.
 *
 * It is a dashboard strategy: Home Assistant runs it when the dashboard opens,
 * and again when entities or devices are added or removed, such as the
 * phenomena of a new bulletin. Users add it from Settings → Dashboards → Add
 * dashboard → Community dashboards. The integration serves this file and has
 * the frontend load it (custom_components/dpc/dashboard.py).
 *
 * The entities are found by their translation key, never by their entity ID,
 * which users can rename.
 */

/**
 * @typedef {object} EntityEntry The registry entry of an entity, as the frontend has it.
 * @property {string} entity_id
 * @property {string} platform The integration of the entity.
 * @property {string | null} [device_id]
 * @property {string | null} [translation_key]
 * @property {boolean} [hidden]
 *
 * @typedef {object} DeviceEntry The registry entry of a device: a DPC place.
 * @property {string} id
 * @property {string | null} [name]
 * @property {string | null} [name_by_user]
 *
 * @typedef {object} Hass The parts of the Home Assistant object the strategy reads.
 * @property {Record<string, EntityEntry>} entities
 * @property {Record<string, DeviceEntry>} devices
 * @property {{ version: string }} config
 * @property {{ language: string }} [locale]
 * @property {string} [language]
 *
 * @typedef {Record<string, any>} Card A card configuration.
 * @typedef {{ type: string, cards: Card[] }} Section A section of a sections view.
 */

/** The integration whose entities the dashboard shows. */
export const PLATFORM = "dpc";

/** The name of the strategy, `custom:dpc-alert` in a dashboard or a view. */
export const STRATEGY = "dpc-alert";

const ICON = "mdi:shield-alert";

/** The binary sensors of the risks of today and tomorrow, by translation key. */
export const RISK_SENSORS = [
  "idraulico_oggi",
  "temporali_oggi",
  "idrogeologico_oggi",
  "idraulico_domani",
  "temporali_domani",
  "idrogeologico_domani",
];

/** Color of each state of the alert sensors of a day. */
export const ALERT_COLORS = {
  green: "green",
  yellow: "yellow",
  orange: "orange",
  red: "red",
};

/** Color of each state of the precipitation sensors, as on the DPC vigilance map. */
export const PRECIPITATION_COLORS = {
  none: "green",
  light: "light-blue",
  moderate: "blue",
  heavy: "indigo",
  very_heavy: "deep-purple",
};

/** Color of each alert level of a risk, its `level` attribute: 1 green to 4 red. */
export const RISK_LEVEL_COLORS = { 1: "green", 2: "yellow", 3: "orange", 4: "red" };

/** The first versions of Home Assistant with the features the dashboard uses. */
const ALERT_CARD_VERSION = [2026, 9];
const ENTITY_NAME_VERSION = [2025, 11];
const NO_DATA_STATES = ["unknown", "unavailable"];

/** The texts of the dashboard, in the languages of the integration. */
// Keep each integration_name in sync with the top-level title in translations/*.json.
const TEXTS = {
  en: {
    integration_name: "Civil Protection Department",
    criticality: "Alerts",
    vigilance: "Weather vigilance",
    description:
      "Alerts and weather vigilance of the Civil Protection Department for your places in Italy.",
    no_places:
      "Add a place of the Civil Protection Department integration to see its alerts here.",
  },
  it: {
    integration_name: "Dipartimento Protezione Civile",
    criticality: "Allerte",
    vigilance: "Vigilanza meteo",
    description:
      "Allerte e vigilanza meteo del Dipartimento della Protezione Civile per i tuoi luoghi in Italia.",
    no_places:
      "Aggiungi un luogo dell'integrazione Dipartimento Protezione Civile per vederne qui le allerte.",
  },
  "pt-BR": {
    integration_name: "Defesa Civil",
    criticality: "Alertas",
    vigilance: "Vigilância meteorológica",
    description:
      "Alertas e vigilância meteorológica da Defesa Civil para os seus lugares na Itália.",
    no_places:
      "Adicione um lugar da integração Defesa Civil para ver os alertas dele aqui.",
  },
  fr: {
    integration_name: "Département de la Protection civile",
    criticality: "Alertes",
    vigilance: "Vigilance météo",
    description:
      "Alertes et vigilance météo du Département de la Protection civile pour vos lieux en Italie.",
    no_places:
      "Ajoutez un lieu de l'intégration Département de la Protection civile pour voir ses alertes ici.",
  },
  de: {
    integration_name: "Zivilschutzabteilung",
    criticality: "Warnungen",
    vigilance: "Wetterlage",
    description:
      "Warnungen und Wetterlage des Zivilschutzes für Ihre Orte in Italien.",
    no_places:
      "Fügen Sie einen Ort der Integration Zivilschutzabteilung hinzu, um hier seine Warnungen zu sehen.",
  },
  es: {
    integration_name: "Departamento de Protección Civil",
    criticality: "Alertas",
    vigilance: "Vigilancia meteorológica",
    description:
      "Alertas y vigilancia meteorológica del Departamento de Protección Civil para tus lugares en Italia.",
    no_places:
      "Añade un lugar de la integración Departamento de Protección Civil para ver aquí sus alertas.",
  },
};

/**
 * Return the texts in a language: its own, those of its base language
 * (`it` for `it-CH`, `pt-BR` for `pt`), or English.
 *
 * @param {string | undefined} language
 */
export function textsIn(language) {
  const base = (language ?? "en").split("-")[0];
  const match =
    Object.keys(TEXTS).find((known) => known === language) ??
    Object.keys(TEXTS).find((known) => known.split("-")[0] === base) ??
    "en";
  return TEXTS[/** @type {keyof typeof TEXTS} */ (match)];
}

/**
 * Return the localized dashboard creation suggestion.
 *
 * @param {string | undefined} language
 */
export function dashboardSuggestion(language) {
  return { title: textsIn(language).integration_name, icon: ICON };
}

/**
 * Return whether Home Assistant is at least the given year and month version.
 *
 * @param {Hass} hass
 * @param {number[]} version e.g. [2026, 9]
 */
export function isAtLeast(hass, [year, month]) {
  const [major, minor] = hass.config.version.split(".").map(Number);
  return major > year || (major === year && minor >= month);
}

/** A DPC place: its device and its entities, by domain and translation key. */
export class Place {
  /**
   * @param {DeviceEntry} device
   * @param {EntityEntry[]} entities
   */
  constructor(device, entities) {
    this.device = device;
    this.entries = entities;
  }

  /** The name of the place, as the user sees its device. */
  get name() {
    return this.device.name_by_user || this.device.name || "DPC";
  }

  /**
   * Return the entity ID of an entity of the place, if it is enabled.
   *
   * @param {string} domain e.g. "sensor"
   * @param {string} translationKey e.g. "alert_today"
   */
  entity(domain, translationKey) {
    return this.entries.find(
      (entry) =>
        entry.entity_id.startsWith(`${domain}.`) &&
        entry.translation_key === translationKey,
    )?.entity_id;
  }

  /**
   * Return the entity IDs of all the entities of a domain, e.g. the phenomena.
   *
   * @param {string} domain
   */
  entitiesOf(domain) {
    return this.entries
      .filter((entry) => entry.entity_id.startsWith(`${domain}.`))
      .map((entry) => entry.entity_id)
      .sort();
  }
}

/**
 * Return the DPC places, from the devices of the visible DPC entities.
 *
 * @param {Hass} hass
 * @returns {Place[]}
 */
export function findPlaces(hass) {
  /** @type {Map<string, EntityEntry[]>} */
  const entitiesByDevice = new Map();
  for (const entry of Object.values(hass.entities)) {
    if (entry.platform !== PLATFORM || !entry.device_id || entry.hidden) {
      continue;
    }
    const entities = entitiesByDevice.get(entry.device_id) ?? [];
    entities.push(entry);
    entitiesByDevice.set(entry.device_id, entities);
  }
  return [...entitiesByDevice]
    .filter(([deviceId]) => hass.devices[deviceId])
    .map(([deviceId, entities]) => new Place(hass.devices[deviceId], entities))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Return a URL path made of a name: "Città di Castello" is "citta-di-castello".
 *
 * @param {string} name
 */
export function slugify(name) {
  return (
    name
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || "dpc"
  );
}

/**
 * Return the variants of a card, one per state, each in the color of its
 * state and visible only in that state; and the card without color for the
 * other states, such as unknown.
 *
 * Cards have a fixed color: the variants give them the color of the state.
 *
 * @param {Card} card
 * @param {string} entity
 * @param {Record<string, string>} colors The color of each state.
 * @param {string} colorOption The option of the card that sets its color.
 * @returns {Card[]}
 */
export function colorByState(card, entity, colors, colorOption = "color") {
  const states = Object.keys(colors);
  return [
    ...states.map((state) => ({
      ...card,
      [colorOption]: colors[state],
      visibility: [{ condition: "state", entity, state }],
    })),
    {
      ...card,
      visibility: [
        { condition: "state", entity, state_not: [...states, ...NO_DATA_STATES] },
      ],
    },
  ];
}

/**
 * Return the banners of a risk, shown while it is on, in the color of its level.
 *
 * Before the alert card, a tile shown while it is on.
 *
 * @param {Hass} hass
 * @param {string} entity A binary sensor of a risk.
 * @returns {Card[]}
 */
export function riskBanners(hass, entity) {
  const isOn = { condition: "state", entity, state: "on" };
  if (!isAtLeast(hass, ALERT_CARD_VERSION)) {
    return [{ ...tile(hass, entity), visibility: [isOn] }];
  }
  return Object.entries(RISK_LEVEL_COLORS).map(([level, color]) => ({
    type: "alert",
    entity,
    name: { type: "entity" },
    alert_color: color,
    hide_state: true,
    visibility: [
      isOn,
      {
        condition: "numeric_state",
        entity,
        attribute: "level",
        above: Number(level) - 1,
        below: Number(level) + 1,
      },
    ],
  }));
}

/**
 * Return a tile of an entity, named without the place when Home Assistant can.
 *
 * @param {Hass} hass
 * @param {string} entity
 * @param {Card} [options]
 * @returns {Card}
 */
export function tile(hass, entity, options = {}) {
  const name = isAtLeast(hass, ENTITY_NAME_VERSION)
    ? { name: { type: "entity" } }
    : {};
  return { type: "tile", entity, ...name, ...options };
}

/**
 * Return the picture of a map of the bulletin.
 *
 * @param {string} entity An image entity.
 * @returns {Card}
 */
function mapPicture(entity) {
  return {
    type: "picture-entity",
    entity,
    show_state: false,
    grid_options: { columns: 6 },
    visibility: [{ condition: "state", entity, state_not: NO_DATA_STATES }],
  };
}

/**
 * Return the section of the criticality bulletin: the alert of each day, the
 * risks on, and the maps.
 *
 * @param {Hass} hass
 * @param {Place} place
 * @returns {Section}
 */
export function criticalitySection(hass, place) {
  const texts = textsIn(hass.locale?.language ?? hass.language);
  const days = ["alert_today", "alert_tomorrow"]
    .map((key) => place.entity("sensor", key))
    .filter((entity) => entity !== undefined);
  const risks = RISK_SENSORS.map((key) => place.entity("binary_sensor", key)).filter(
    (entity) => entity !== undefined,
  );
  const maps = ["criticality_map_today", "criticality_map_tomorrow"]
    .map((key) => place.entity("image", key))
    .filter((entity) => entity !== undefined);
  return {
    type: "grid",
    cards: [
      { type: "heading", heading: texts.criticality, icon: ICON },
      ...days.flatMap((entity) =>
        colorByState(
          tile(hass, entity, { state_content: ["state", "risks"] }),
          entity,
          ALERT_COLORS,
        ),
      ),
      ...risks.flatMap((entity) => riskBanners(hass, entity)),
      ...maps.map(mapPicture),
    ],
  };
}

/**
 * Return the section of the vigilance bulletin: the precipitation of each day,
 * the phenomena near the place on a map, and the maps of the bulletin.
 *
 * @param {Hass} hass
 * @param {Place} place
 * @returns {Section}
 */
export function vigilanceSection(hass, place) {
  const texts = textsIn(hass.locale?.language ?? hass.language);
  const days = ["precipitation_today", "precipitation_tomorrow", "precipitation_aftertomorrow"]
    .map((key) => place.entity("sensor", key))
    .filter((entity) => entity !== undefined);
  const phenomena = place.entitiesOf("geo_location");
  const maps = ["vigilance_map_today", "vigilance_map_tomorrow"]
    .map((key) => place.entity("image", key))
    .filter((entity) => entity !== undefined);
  return {
    type: "grid",
    cards: [
      { type: "heading", heading: texts.vigilance, icon: "mdi:weather-pouring" },
      ...days.flatMap((entity) =>
        colorByState(
          tile(hass, entity, { grid_options: { columns: 4 } }),
          entity,
          PRECIPITATION_COLORS,
        ),
      ),
      ...(phenomena.length
        ? [
            {
              type: "map",
              entities: phenomena.map((entity) => ({ entity })),
              grid_options: { columns: 12 },
            },
          ]
        : []),
      ...maps.map(mapPicture),
    ],
  };
}

/**
 * Return the view of a place.
 *
 * @param {Hass} hass
 * @param {Place} place
 */
export function placeView(hass, place) {
  return {
    type: "sections",
    max_columns: 2,
    sections: [criticalitySection(hass, place), vigilanceSection(hass, place)],
  };
}

/**
 * Return the dashboard: a view per place, each built by the view strategy.
 *
 * @param {Hass} hass
 */
export function generateDashboard(hass) {
  const places = findPlaces(hass);
  if (!places.length) {
    const texts = textsIn(hass.locale?.language ?? hass.language);
    return {
      views: [
        {
          type: "panel",
          cards: [{ type: "markdown", content: texts.no_places }],
        },
      ],
    };
  }
  /** @type {Set<string>} */
  const paths = new Set();
  return {
    views: places.map((place) => {
      let path = slugify(place.name);
      for (let number = 2; paths.has(path); number += 1) {
        path = `${slugify(place.name)}-${number}`;
      }
      paths.add(path);
      return {
        title: place.name,
        path,
        icon: ICON,
        strategy: { type: `custom:${STRATEGY}`, device_id: place.device.id },
      };
    }),
  };
}

/**
 * Return the view of the place of a device, for `custom:dpc-alert` in a view.
 *
 * @param {{ device_id?: string }} config
 * @param {Hass} hass
 */
export function generateView(config, hass) {
  const place = findPlaces(hass).find(
    (candidate) => candidate.device.id === config.device_id,
  );
  if (!place) {
    const texts = textsIn(hass.locale?.language ?? hass.language);
    return { type: "panel", cards: [{ type: "markdown", content: texts.no_places }] };
  }
  return placeView(hass, place);
}

// The strategies, as Home Assistant looks them up: a custom element per kind,
// with static methods. Not defined outside a browser, as in the tests.

/** Rebuild the dashboard when DPC entities or places come and go. */
const REGISTRY_DEPENDENCIES = ["entities", "devices"];

if (globalThis.customElements && globalThis.HTMLElement) {
  class DpcDashboardStrategy extends HTMLElement {
    static registryDependencies = REGISTRY_DEPENDENCIES;

    static noEditor = true;

    /** @param {unknown} _config @param {Hass} hass */
    static async generate(_config, hass) {
      return generateDashboard(hass);
    }

    static getCreateSuggestions() {
      return dashboardSuggestion(document.documentElement.lang || navigator.language);
    }
  }

  class DpcViewStrategy extends HTMLElement {
    static registryDependencies = REGISTRY_DEPENDENCIES;

    /** @param {{ device_id?: string }} config @param {Hass} hass */
    static async generate(config, hass) {
      return generateView(config, hass);
    }
  }

  /** @param {string} tag @param {CustomElementConstructor} strategy */
  const define = (tag, strategy) =>
    customElements.get(tag) || customElements.define(tag, strategy);
  define(`ll-strategy-dashboard-${STRATEGY}`, DpcDashboardStrategy);
  define(`ll-strategy-view-${STRATEGY}`, DpcViewStrategy);

  // Listed under Community dashboards in the Add dashboard dialog
  const strategies = /** @type {any} */ (window).customStrategies ?? [];
  /** @type {any} */ (window).customStrategies = strategies;
  if (!strategies.some((/** @type {{ type: string }} */ item) => item.type === STRATEGY)) {
    strategies.push({
      type: STRATEGY,
      strategyType: "dashboard",
      name: "DPC Alert",
      description: textsIn(document.documentElement.lang || navigator.language)
        .description,
      documentationURL:
        "https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert#dashboard",
    });
  }
}
