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
 * The entities are found by their translation key and the day of their
 * device, never by their entity ID, which users can rename. A place is a
 * device; each of its days is a device linked to it (`via_device_id`).
 */

/**
 * @typedef {object} EntityEntry The registry entry of an entity, as the frontend has it.
 * @property {string} entity_id
 * @property {string} platform The integration of the entity.
 * @property {string | null} [device_id]
 * @property {string | null} [translation_key]
 * @property {boolean} [hidden]
 *
 * @typedef {object} DeviceEntry The registry entry of a device: a DPC place or a day of it.
 * @property {string} id
 * @property {string | null} [name]
 * @property {string | null} [name_by_user]
 * @property {Array<Array<string | number>>} [identifiers] e.g. [["dpc", "41.9_12.5-today"]]
 * @property {string | null} [via_device_id] The place of a day.
 *
 * @typedef {object} PlaceEntity An entity of a place, and its day.
 * @property {EntityEntry} entry
 * @property {string | null} day "today", "tomorrow" or "aftertomorrow"; null for the place.
 *
 * @typedef {object} Hass The parts of the Home Assistant object the strategy reads.
 * @property {Record<string, EntityEntry>} entities
 * @property {Record<string, DeviceEntry>} devices
 * @property {{ version: string }} config
 * @property {{ language: string }} [locale]
 * @property {string} [language]
 * @property {(key: string, values?: Record<string, string>) => string} [localize]
 *   The texts of the frontend, in the language of the user.
 * @property {(category: string, integration: string) => Promise<Hass["localize"]>} [loadBackendTranslation]
 *   Load texts of an integration into the frontend, and return them with the others.
 *
 * @typedef {Record<string, any>} Card A card configuration.
 * @typedef {{ type: string, cards: Card[] }} Section A section of a sections view.
 */

/** The integration whose entities the dashboard shows. */
export const PLATFORM = "dpc";

/** The name of the strategy, `custom:dpc-alert` in a dashboard or a view. */
export const STRATEGY = "dpc-alert";

/** The icon of a place, in the dashboard and in the card. */
export const ICON = "mdi:shield-alert";

/** The days of the bulletins, as the identifiers of the devices of the days end. */
export const DAYS = ["today", "tomorrow", "aftertomorrow"];

/** The binary sensors of the risks of a day, by translation key. */
export const RISK_SENSORS = ["hydraulic_risk", "thunderstorm_risk", "hydrogeological_risk"];

/** The criticalities of a day with an alert, and the risks its map shows. */
const CRITICALITIES = ["ordinary", "moderate", "high"];
const RISKS = ["hydraulic", "thunderstorms", "hydrogeological"];

/** The colors of the alert levels on the DPC criticality map: none, yellow, orange, red. */
const DPC_ALERT_COLORS = ["#90c985", "#f8f865", "#f0bf01", "#fd6767"];

/**
 * The colors of the precipitation, none to very heavy.
 *
 * Light to very heavy have the scale of the alerts, green to red, so that a
 * level reads the same whatever it measures: the vigilance map draws them in
 * blues and purples. No precipitation has the color Home Assistant gives the
 * icons of sensors, a blue: the map draws it white, which a light theme does
 * not show.
 */
const DPC_PRECIPITATION_COLORS = ["var(--state-icon-color)", ...DPC_ALERT_COLORS];

/** Color of each state of the alert of a day, and of the level of each risk. */
export const ALERT_COLORS = Object.fromEntries(
  ["green", "yellow", "orange", "red"].map((level, index) => [level, DPC_ALERT_COLORS[index]]),
);

/** Color of each state of the highest alert of a place: 1 to 4. */
export const HIGHEST_ALERT_COLORS = Object.fromEntries(
  DPC_ALERT_COLORS.map((color, index) => [String(index + 1), color]),
);

/** Color of each state of the criticality of a day: the color of its level. */
export const CRITICALITY_COLORS = Object.fromEntries([
  ["absent", DPC_ALERT_COLORS[0]],
  ...CRITICALITIES.flatMap((criticality, index) =>
    RISKS.map((risk) => [`${criticality}_${risk}`, DPC_ALERT_COLORS[index + 1]]),
  ),
]);

/** Color of each state of the precipitation of a day. */
export const PRECIPITATION_COLORS = Object.fromEntries(
  ["none", "light", "moderate", "heavy", "very_heavy"].map((amount, index) => [
    amount,
    DPC_PRECIPITATION_COLORS[index],
  ]),
);

/** Color of each state of the highest precipitation of a place: 1 to 5. */
export const HIGHEST_PRECIPITATION_COLORS = Object.fromEntries(
  DPC_PRECIPITATION_COLORS.map((color, index) => [String(index + 1), color]),
);

/** The diagnostic sensors of a place, by translation key. */
const BULLETIN_SENSORS = [
  "alert_zone",
  "vigilance_zone",
  "criticality_bulletin",
  "vigilance_bulletin",
  "criticality_valid_until",
  "vigilance_valid_until",
];

/** The first versions of Home Assistant with the features the dashboard uses. */
const ALERT_CARD_VERSION = [2026, 9];
const ENTITY_NAME_VERSION = [2025, 11];
/** States of an entity without data, such as the map of tomorrow after midnight. */
export const NO_DATA_STATES = ["unknown", "unavailable"];

/** The texts of the dashboard and of the editor of the cards, in the languages of the integration. */
// Keep each integration_name in sync with the top-level title in translations/*.json.
const TEXTS = {
  en: {
    integration_name: "Civil Protection Department",
    bulletins: "Bulletins",
    maps: "Maps",
    place: "Place",
    title: "Title",
    heading: "Heading",
    days: "Days",
    columns: "Columns",
    description:
      "Alerts and weather vigilance of the Civil Protection Department for your places in Italy.",
    no_places:
      "Add a place of the Civil Protection Department integration to see its alerts here.",
  },
  it: {
    integration_name: "Dipartimento Protezione Civile",
    bulletins: "Bollettini",
    maps: "Mappe",
    place: "Luogo",
    title: "Titolo",
    heading: "Intestazione",
    days: "Giorni",
    columns: "Colonne",
    description:
      "Allerte e vigilanza meteo del Dipartimento della Protezione Civile per i tuoi luoghi in Italia.",
    no_places:
      "Aggiungi un luogo dell'integrazione Dipartimento Protezione Civile per vederne qui le allerte.",
  },
  "pt-BR": {
    integration_name: "Defesa Civil",
    bulletins: "Boletins",
    maps: "Mapas",
    place: "Lugar",
    title: "Título",
    heading: "Cabeçalho",
    days: "Dias",
    columns: "Colunas",
    description:
      "Alertas e vigilância meteorológica da Defesa Civil para os seus lugares na Itália.",
    no_places:
      "Adicione um lugar da integração Defesa Civil para ver os alertas dele aqui.",
  },
  fr: {
    integration_name: "Département de la Protection civile",
    bulletins: "Bulletins",
    maps: "Cartes",
    place: "Lieu",
    title: "Titre",
    heading: "En-tête",
    days: "Jours",
    columns: "Colonnes",
    description:
      "Alertes et vigilance météo du Département de la Protection civile pour vos lieux en Italie.",
    no_places:
      "Ajoutez un lieu de l'intégration Département de la Protection civile pour voir ses alertes ici.",
  },
  de: {
    integration_name: "Zivilschutzabteilung",
    bulletins: "Bulletins",
    maps: "Karten",
    place: "Ort",
    title: "Titel",
    heading: "Kopfzeile",
    days: "Tage",
    columns: "Spalten",
    description:
      "Warnungen und Wetterlage des Zivilschutzes für Ihre Orte in Italien.",
    no_places:
      "Fügen Sie einen Ort der Integration Zivilschutzabteilung hinzu, um hier seine Warnungen zu sehen.",
  },
  es: {
    integration_name: "Departamento de Protección Civil",
    bulletins: "Boletines",
    maps: "Mapas",
    place: "Lugar",
    title: "Título",
    heading: "Encabezado",
    days: "Días",
    columns: "Columnas",
    description:
      "Alertas y vigilancia meteorológica del Departamento de Protección Civil para tus lugares en Italia.",
    no_places:
      "Añade un lugar de la integración Departamento de Protección Civil para ver aquí sus alertas.",
  },
  "zh-Hans": {
    integration_name: "意大利民防部",
    bulletins: "公报",
    maps: "地图",
    place: "地点",
    title: "标题",
    heading: "标题栏",
    days: "日期",
    columns: "列数",
    description:
      "意大利民防部为您在意大利的地点提供的预警和气象警戒。",
    no_places:
      "添加意大利民防部集成的地点，即可在此查看其预警。",
  },
  ro: {
    integration_name: "Departamentul Protecției Civile",
    bulletins: "Buletine",
    maps: "Hărți",
    place: "Loc",
    title: "Titlu",
    heading: "Antet",
    days: "Zile",
    columns: "Coloane",
    description:
      "Alertele și vigilența meteorologică ale Departamentului Protecției Civile pentru locurile tale din Italia.",
    no_places:
      "Adaugă un loc al integrării Departamentul Protecției Civile pentru a-i vedea alertele aici.",
  },
  ar: {
    integration_name: "إدارة الحماية المدنية",
    bulletins: "النشرات",
    maps: "الخرائط",
    place: "المكان",
    title: "العنوان",
    heading: "الترويسة",
    days: "الأيام",
    columns: "الأعمدة",
    description:
      "إنذارات ويقظة الطقس من إدارة الحماية المدنية لأماكنك في إيطاليا.",
    no_places:
      "أضف مكاناً من تكامل إدارة الحماية المدنية لرؤية إنذاراته هنا.",
  },
  uk: {
    integration_name: "Департамент цивільного захисту",
    bulletins: "Бюлетені",
    maps: "Карти",
    place: "Місце",
    title: "Заголовок",
    heading: "Шапка",
    days: "Дні",
    columns: "Стовпці",
    description:
      "Попередження та метеорологічна пильність Департаменту цивільного захисту для ваших місць в Італії.",
    no_places:
      "Додайте місце інтеграції «Департамент цивільного захисту», щоб побачити тут його попередження.",
  },
  sq: {
    integration_name: "Departamenti i Mbrojtjes Civile",
    bulletins: "Buletinet",
    maps: "Hartat",
    place: "Vendi",
    title: "Titulli",
    heading: "Koka",
    days: "Ditët",
    columns: "Kolonat",
    description:
      "Paralajmërimet dhe vigjilenca meteorologjike e Departamentit të Mbrojtjes Civile për vendet e tua në Itali.",
    no_places:
      "Shto një vend të integrimit Departamenti i Mbrojtjes Civile për të parë këtu paralajmërimet e tij.",
  },
  bn: {
    integration_name: "নাগরিক সুরক্ষা বিভাগ",
    bulletins: "বুলেটিন",
    maps: "মানচিত্র",
    place: "জায়গা",
    title: "শিরোনাম",
    heading: "হেডার",
    days: "দিন",
    columns: "কলাম",
    description:
      "ইতালিতে আপনার জায়গাগুলোর জন্য নাগরিক সুরক্ষা বিভাগের সতর্কতা ও আবহাওয়া নজরদারি।",
    no_places:
      "এখানে সতর্কতা দেখতে নাগরিক সুরক্ষা বিভাগ ইন্টিগ্রেশনের একটি জায়গা যোগ করুন।",
  },
  hi: {
    integration_name: "नागरिक सुरक्षा विभाग",
    bulletins: "बुलेटिन",
    maps: "मानचित्र",
    place: "स्थान",
    title: "शीर्षक",
    heading: "हेडर",
    days: "दिन",
    columns: "कॉलम",
    description:
      "इटली में आपके स्थानों के लिए नागरिक सुरक्षा विभाग की चेतावनियाँ और मौसम सतर्कता।",
    no_places:
      "यहाँ इसकी चेतावनियाँ देखने के लिए नागरिक सुरक्षा विभाग इंटीग्रेशन का एक स्थान जोड़ें।",
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
 * Return Home Assistant with the texts of the integration in the language of
 * the user. The frontend has the names of the entities; the names of the days
 * are those of the devices, which it loads when asked.
 *
 * @param {Hass} hass
 * @returns {Promise<Hass>}
 */
export async function withTexts(hass) {
  if (!hass.loadBackendTranslation) {
    return hass;
  }
  await hass.loadBackendTranslation("entity", PLATFORM);
  const localize = await hass.loadBackendTranslation("device", PLATFORM);
  return { ...hass, localize };
}

/**
 * Return a text of the integration in the language of the user, if the
 * frontend has it.
 *
 * @param {Hass} hass
 * @param {string} key e.g. "entity.sensor.precipitation.name"
 * @param {Record<string, string>} [values]
 */
export function translated(hass, key, values) {
  return hass.localize?.(`component.${PLATFORM}.${key}`, values) || undefined;
}

/**
 * Return the name of an entity of the integration in the language of the
 * user, from its translation key: "Precipitação" for the precipitation of a
 * day. Home Assistant names entities in the language of the server.
 *
 * @param {Hass} hass
 * @param {string} entity
 */
export function entityName(hass, entity) {
  const key = hass.entities[entity]?.translation_key;
  return key ? translated(hass, `entity.${entity.split(".")[0]}.${key}.name`) : undefined;
}

/**
 * Return the name of a day of a place in the language of the user: the name
 * the user gave its device, or the name of the days of the integration
 * ("Hoje"), or else the name of its device, in the language of the server.
 *
 * @param {Hass} hass
 * @param {Place} place
 * @param {string} day
 */
export function dayName(hass, place, day) {
  if (place.days.get(day)?.name_by_user) {
    return place.dayName(day);
  }
  const name = translated(hass, `device.${day}.name`, { place: place.name });
  if (!name) {
    return place.dayName(day);
  }
  const prefix = `${place.name} · `;
  return name.startsWith(prefix) ? name.slice(prefix.length) : name;
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

/** A DPC place: its device and its entities, by domain, translation key and day. */
export class Place {
  /**
   * @param {DeviceEntry} device
   * @param {PlaceEntity[]} entities
   * @param {Map<string, DeviceEntry>} [days] The device of each day, by day.
   */
  constructor(device, entities, days = new Map()) {
    this.device = device;
    this.entries = entities;
    this.days = days;
  }

  /** The name of the place, as the user sees its device. */
  get name() {
    return this.device.name_by_user || this.device.name || "DPC";
  }

  /**
   * Return the entity ID of an entity of the place or of a day, if it is enabled.
   *
   * @param {string} domain e.g. "sensor"
   * @param {string} translationKey e.g. "alert"
   * @param {string | null} [day] e.g. "today"; none for an entity of the place
   */
  entity(domain, translationKey, day = null) {
    return this.entries.find(
      ({ entry, day: dayOfEntry }) =>
        entry.entity_id.startsWith(`${domain}.`) &&
        entry.translation_key === translationKey &&
        dayOfEntry === day,
    )?.entry.entity_id;
  }

  /**
   * Return the entity IDs of all the entities of a domain on a day, e.g. the phenomena.
   *
   * @param {string} domain
   * @param {string} day
   */
  entitiesOf(domain, day) {
    return this.entries
      .filter(
        ({ entry, day: dayOfEntry }) =>
          entry.entity_id.startsWith(`${domain}.`) && dayOfEntry === day,
      )
      .map(({ entry }) => entry.entity_id)
      .sort();
  }

  /**
   * Return the name of a day of the place, as its device says it: "Hoje" for
   * "Milano · Hoje", or the name the user gave the device.
   *
   * @param {string} day
   */
  dayName(day) {
    const device = this.days.get(day);
    const name = device?.name_by_user || device?.name || day;
    const prefix = `${this.name} · `;
    return name.startsWith(prefix) ? name.slice(prefix.length) : name;
  }
}

/**
 * Return the day of the device of a day, from its identifier; null for a place.
 *
 * @param {DeviceEntry} device
 */
export function dayOf(device) {
  for (const [domain, id] of device.identifiers ?? []) {
    const day = DAYS.find((candidate) => String(id).endsWith(`-${candidate}`));
    if (domain === PLATFORM && day) {
      return day;
    }
  }
  return null;
}

/**
 * Return the DPC places, from the devices of the visible DPC entities.
 *
 * @param {Hass} hass
 * @returns {Place[]}
 */
export function findPlaces(hass) {
  /** @type {Map<string, PlaceEntity[]>} */
  const entitiesByPlace = new Map();
  /** @type {Map<string, Map<string, DeviceEntry>>} */
  const daysByPlace = new Map();
  for (const entry of Object.values(hass.entities)) {
    const device = entry.device_id ? hass.devices[entry.device_id] : undefined;
    if (entry.platform !== PLATFORM || !device || entry.hidden) {
      continue;
    }
    // The entities of a day belong to the place of its device
    const day = dayOf(device);
    const placeId = (day && device.via_device_id) || device.id;
    const entities = entitiesByPlace.get(placeId) ?? [];
    entities.push({ entry, day });
    entitiesByPlace.set(placeId, entities);
    if (day) {
      const days = daysByPlace.get(placeId) ?? new Map();
      days.set(day, device);
      daysByPlace.set(placeId, days);
    }
  }
  return [...entitiesByPlace]
    .filter(([placeId]) => hass.devices[placeId])
    .map(
      ([placeId, entities]) =>
        new Place(hass.devices[placeId], entities, daysByPlace.get(placeId)),
    )
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
 * state and visible only in that state; and the card without color for any
 * other state. Without data (unknown, unavailable), the card is hidden.
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
 * Before the alert card, a tile shown while it is on. Without the level of the
 * risk, as when the place shows no sensors, the risk is all the dashboard has
 * of it: its tile, always shown, as the levels are.
 *
 * @param {Hass} hass
 * @param {string} entity A binary sensor of a risk.
 * @param {string} [level] The sensor of the level of the same risk and day.
 * @returns {Card[]}
 */
export function riskBanners(hass, entity, level) {
  if (!level) {
    return [tile(hass, entity, { grid_options: { columns: 4 } })];
  }
  const isOn = { condition: "state", entity, state: "on" };
  if (!isAtLeast(hass, ALERT_CARD_VERSION)) {
    return [{ ...tile(hass, entity), visibility: [isOn] }];
  }
  return Object.entries(ALERT_COLORS).map(([state, color]) => ({
    type: "alert",
    entity,
    name: entityName(hass, entity) ?? { type: "entity" },
    alert_color: color,
    hide_state: true,
    visibility: [isOn, { condition: "state", entity: level, state }],
  }));
}

/**
 * Return a tile of an entity, named in the language of the user, or else
 * without the place when Home Assistant can.
 *
 * @param {Hass} hass
 * @param {string} entity
 * @param {Card} [options]
 * @returns {Card}
 */
export function tile(hass, entity, options = {}) {
  const translatedName = entityName(hass, entity);
  /** @type {Card} */
  let name = {};
  if (translatedName) {
    name = { name: translatedName };
  } else if (isAtLeast(hass, ENTITY_NAME_VERSION)) {
    name = { name: { type: "entity" } };
  }
  return { type: "tile", entity, ...name, ...options };
}

/**
 * Return the picture of a map of the bulletin, named in the language of the user.
 *
 * @param {Hass} hass
 * @param {string} entity An image entity.
 * @returns {Card}
 */
function mapPicture(hass, entity) {
  const name = entityName(hass, entity);
  return {
    type: "picture-entity",
    entity,
    ...(name ? { name } : {}),
    show_state: false,
    grid_options: { columns: 6 },
    visibility: [{ condition: "state", entity, state_not: NO_DATA_STATES }],
  };
}

/**
 * Return the tile of an entity in the color of its state; none without the entity.
 *
 * @param {Hass} hass
 * @param {string | undefined} entity
 * @param {Record<string, string>} colors
 * @param {Card} [options]
 * @returns {Card[]}
 */
function coloredTile(hass, entity, colors, options = {}) {
  return entity ? colorByState(tile(hass, entity, options), entity, colors) : [];
}

/**
 * Return the tiles of entities, those that are enabled.
 *
 * @param {Hass} hass
 * @param {Array<string | undefined>} entities
 * @param {Card} [options]
 * @returns {Card[]}
 */
function tiles(hass, entities, options = {}) {
  return entities.flatMap((entity) => (entity ? [tile(hass, entity, options)] : []));
}

/**
 * Return the section of the whole place: its highest alert and precipitation,
 * in the colors of DPC, then its zones, when each bulletin was published, and
 * until when each covers.
 *
 * @param {Hass} hass
 * @param {Place} place
 * @returns {Section}
 */
export function placeSection(hass, place) {
  const half = { grid_options: { columns: 6 } };
  return {
    type: "grid",
    cards: [
      { type: "heading", heading: place.name, icon: ICON },
      ...coloredTile(hass, place.entity("sensor", "highest_alert"), HIGHEST_ALERT_COLORS, half),
      ...coloredTile(
        hass,
        place.entity("sensor", "highest_precipitation"),
        HIGHEST_PRECIPITATION_COLORS,
        half,
      ),
      ...tiles(
        hass,
        BULLETIN_SENSORS.map((key) => place.entity("sensor", key)),
        half,
      ),
    ],
  };
}

/**
 * Return the section of a day: a banner for each risk on, the alert and the
 * criticality, the maps of the bulletins and the phenomena near the place on a
 * map, then the level of each risk, the precipitation and the number of
 * phenomena.
 *
 * The maps come right after cards as wide as the section, so that the two maps
 * of the bulletins start a row together, rather than one of them filling the
 * room a smaller card left.
 *
 * @param {Hass} hass
 * @param {Place} place
 * @param {string} day e.g. "today"
 * @returns {Section}
 */
export function daySection(hass, place, day) {
  /** @param {string} domain @param {string} key */
  const entity = (domain, key) => place.entity(domain, key, day);
  const phenomena = place.entitiesOf("geo_location", day);
  return {
    type: "grid",
    cards: [
      { type: "heading", heading: dayName(hass, place, day), icon: "mdi:calendar" },
      ...RISK_SENSORS.flatMap((key) => {
        const risk = entity("binary_sensor", key);
        return risk ? riskBanners(hass, risk, entity("sensor", `${key}_level`)) : [];
      }),
      ...coloredTile(hass, entity("sensor", "alert"), ALERT_COLORS, {
        state_content: ["state", "risks"],
        grid_options: { columns: 12 },
      }),
      ...coloredTile(hass, entity("sensor", "criticality"), CRITICALITY_COLORS, {
        grid_options: { columns: 12 },
      }),
      // DPC publishes no vigilance map for the day after tomorrow
      ...["criticality_map", "vigilance_map"]
        .map((key) => entity("image", key))
        .filter((map) => map !== undefined)
        .map((map) => mapPicture(hass, map)),
      ...(phenomena.length
        ? [
            {
              type: "map",
              // The icon of the kind of phenomenon, rather than the initials of its name
              entities: phenomena.map((phenomenon) => ({ entity: phenomenon, label_mode: "icon" })),
              grid_options: { columns: 12 },
            },
          ]
        : []),
      ...RISK_SENSORS.flatMap((key) =>
        coloredTile(hass, entity("sensor", `${key}_level`), ALERT_COLORS, {
          grid_options: { columns: 4 },
        }),
      ),
      ...coloredTile(hass, entity("sensor", "precipitation"), PRECIPITATION_COLORS, {
        grid_options: { columns: 6 },
      }),
      ...tiles(hass, [entity("sensor", "nearby_phenomena")], { grid_options: { columns: 6 } }),
    ],
  };
}

/**
 * Return the view of a place: the sections of the place and of its days that
 * have more than their heading, as when the place shows no sensors.
 *
 * @param {Hass} hass
 * @param {Place} place
 */
export function placeView(hass, place) {
  return {
    type: "sections",
    max_columns: 3,
    sections: [
      placeSection(hass, place),
      ...DAYS.filter((day) => place.days.has(day)).map((day) => daySection(hass, place, day)),
    ].filter((section) => section.cards.length > 1),
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
      // No icon: a tab with an icon shows only the icon, and every place has the same
      return {
        title: place.name,
        path,
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

    /** @param {Hass} hass */
    static getCreateSuggestions(hass) {
      return dashboardSuggestion(hass.locale?.language ?? hass.language);
    }
  }

  class DpcViewStrategy extends HTMLElement {
    static registryDependencies = REGISTRY_DEPENDENCIES;

    /** @param {{ device_id?: string }} config @param {Hass} hass */
    static async generate(config, hass) {
      return generateView(config, await withTexts(hass));
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
