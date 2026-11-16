// Tests of the DPC Alert dashboard strategy: node --test tests/frontend
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  ALERT_COLORS,
  CRITICALITY_COLORS,
  HIGHEST_ALERT_COLORS,
  PRECIPITATION_COLORS,
  colorByState,
  dashboardSuggestion,
  findPlaces,
  generateDashboard,
  generateView,
  isAtLeast,
  slugify,
  textsIn,
} from "../../custom_components/dpc/frontend/dpc-dashboard.js";

/** The days of a place: how entity IDs and device names say them. */
const DAYS = {
  today: { id: "today", name: "Today" },
  tomorrow: { id: "tomorrow", name: "Tomorrow" },
  aftertomorrow: { id: "after_tomorrow", name: "Day after tomorrow" },
};

/** Return the devices of a DPC place: the place, and its days linked to it. */
function placeDevices(id, name) {
  return Object.fromEntries([
    [id, { id, name, identifiers: [["dpc", 41.9, 12.5]] }],
    ...Object.entries(DAYS).map(([day, { name: dayName }]) => [
      `${id}-${day}`,
      {
        id: `${id}-${day}`,
        name: `${name} · ${dayName}`,
        identifiers: [["dpc", `41.900000_12.500000-${day}`]],
        via_device_id: id,
      },
    ]),
  ]);
}

/** Return the registry entries of the entities of a DPC place and of its days. */
function placeEntities(device, prefix, phenomena = []) {
  const entity = (domain, key, day = null) => ({
    entity_id: day ? `${domain}.${prefix}_${DAYS[day].id}_${key}` : `${domain}.${prefix}_${key}`,
    platform: "dpc",
    device_id: day ? `${device}-${day}` : device,
    translation_key: key,
  });
  return [
    ...[
      "highest_alert",
      "highest_precipitation",
      "alert_zone",
      "vigilance_zone",
      "criticality_bulletin",
      "vigilance_bulletin",
      "criticality_valid_until",
      "vigilance_valid_until",
    ].map((key) => entity("sensor", key)),
    ...["today", "tomorrow"].flatMap((day) => [
      entity("sensor", "alert", day),
      entity("sensor", "criticality", day),
      ...["hydraulic_risk", "thunderstorm_risk", "hydrogeological_risk"].flatMap((key) => [
        entity("binary_sensor", key, day),
        entity("sensor", `${key}_level`, day),
      ]),
      entity("image", "criticality_map", day),
      entity("image", "vigilance_map", day),
    ]),
    ...Object.keys(DAYS).flatMap((day) => [
      entity("sensor", "precipitation", day),
      entity("sensor", "nearby_phenomena", day),
    ]),
    ...phenomena.map(([category, day]) => entity("geo_location", category, day)),
  ];
}

/** Return a Home Assistant with the places Roma (with 2 phenomena) and Milano. */
function homeAssistant({ version = "2026.11.0", language = "en", entities = [] } = {}) {
  const all = [
    ...placeEntities("roma", "dpc_roma", [
      ["isolated_thunderstorms_sse", "today"],
      ["moderate_sea_sw", "tomorrow"],
    ]),
    ...placeEntities("milano", "dpc_milano"),
    // Another integration on the same device is not shown
    { entity_id: "sensor.other", platform: "other", device_id: "roma" },
    ...entities,
  ];
  const milano = placeDevices("milano", "Milano");
  milano.milano.name_by_user = null;
  return {
    config: { version },
    locale: { language },
    devices: { ...placeDevices("roma", "Roma"), ...milano },
    entities: Object.fromEntries(all.map((entry) => [entry.entity_id, entry])),
  };
}

/** Return the cards of every section of a view. */
const cardsOf = (view) => view.sections.flatMap((section) => section.cards);

/** Return the cards of an entity in a view. */
const cardsFor = (view, entity) => cardsOf(view).filter((card) => card.entity === entity);

/** Return the color of each state of the cards of an entity colored by state. */
function colorsOf(view, entity) {
  return Object.fromEntries(
    cardsFor(view, entity)
      .filter((card) => card.visibility[0].state !== undefined)
      .map((card) => [card.visibility[0].state, card.color]),
  );
}

describe("dashboard", () => {
  it("has a view per place, sorted by name, built by the view strategy", () => {
    assert.deepEqual(generateDashboard(homeAssistant()).views, [
      {
        title: "Milano",
        path: "milano",
        icon: "mdi:shield-alert",
        strategy: { type: "custom:dpc-alert", device_id: "milano" },
      },
      {
        title: "Roma",
        path: "roma",
        icon: "mdi:shield-alert",
        strategy: { type: "custom:dpc-alert", device_id: "roma" },
      },
    ]);
  });

  it("gives places of the same name different paths", () => {
    const hass = homeAssistant({ entities: placeEntities("peglio2", "dpc_peglio_2") });
    hass.devices.milano.name_by_user = "Peglio";
    Object.assign(hass.devices, placeDevices("peglio2", "Peglio"));

    const paths = generateDashboard(hass).views.map((view) => view.path);

    assert.deepEqual(paths, ["peglio", "peglio-2", "roma"]);
  });

  it("asks for a place when there is none", () => {
    const hass = { ...homeAssistant(), entities: {}, locale: { language: "it" } };

    const [view] = generateDashboard(hass).views;

    assert.match(view.cards[0].content, /Aggiungi un luogo/);
  });

  it("ignores hidden entities and entities without device", () => {
    const hass = homeAssistant({
      entities: [
        { entity_id: "sensor.hidden", platform: "dpc", device_id: "hidden", hidden: true },
        { entity_id: "sensor.loose", platform: "dpc", device_id: null },
      ],
    });

    assert.deepEqual(
      findPlaces(hass).map((place) => place.name),
      ["Milano", "Roma"],
    );
  });

  it("finds the entities of a place on the devices of its days", () => {
    const [, roma] = findPlaces(homeAssistant());

    assert.equal(roma.entity("sensor", "highest_alert"), "sensor.dpc_roma_highest_alert");
    assert.equal(roma.entity("sensor", "alert", "tomorrow"), "sensor.dpc_roma_tomorrow_alert");
    assert.equal(roma.entity("sensor", "alert"), undefined);
    assert.equal(
      roma.entity("sensor", "precipitation", "aftertomorrow"),
      "sensor.dpc_roma_after_tomorrow_precipitation",
    );
  });

  it("leaves out a day whose place is gone", () => {
    const hass = homeAssistant();
    delete hass.devices.milano;

    assert.deepEqual(
      findPlaces(hass).map((place) => place.name),
      ["Roma"],
    );
  });
});

describe("view of a place", () => {
  it("has a section for the place, one for each of its days, and the bulletins", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());

    assert.equal(view.type, "sections");
    // The days as their devices name them, without the place
    assert.deepEqual(
      view.sections.map((section) => section.cards[0].heading),
      ["Roma", "Today", "Tomorrow", "Day after tomorrow", "Bulletins"],
    );
  });

  it("shows only the days the place has", () => {
    const hass = homeAssistant();
    for (const [id, entry] of Object.entries(hass.entities)) {
      if (entry.device_id === "roma-tomorrow") delete hass.entities[id];
    }

    const view = generateView({ device_id: "roma" }, hass);

    assert.deepEqual(
      view.sections.map((section) => section.cards[0].heading),
      ["Roma", "Today", "Day after tomorrow", "Bulletins"],
    );
  });

  it("names a day as the user named its device", () => {
    const hass = homeAssistant();
    hass.devices["roma-today"].name_by_user = "Oggi a casa";

    const view = generateView({ device_id: "roma" }, hass);

    assert.equal(view.sections[1].cards[0].heading, "Oggi a casa");
  });

  it("shows the highest alert and precipitation of the place in the colors of DPC", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());

    assert.deepEqual(colorsOf(view, "sensor.dpc_roma_highest_alert"), {
      1: "#90c985",
      2: "#f8f865",
      3: "#f0bf01",
      4: "#fd6767",
    });
    assert.deepEqual(colorsOf(view, "sensor.dpc_roma_highest_precipitation"), {
      1: "#FFFFFF",
      2: "#C3FFFE",
      3: "#50FFFF",
      4: "#508BFF",
      5: "#A040FF",
    });
  });

  it("shows the alert of each day in the color of its level", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());
    const today = cardsFor(view, "sensor.dpc_roma_today_alert");

    assert.deepEqual(
      today.map((card) => [card.color, card.visibility]),
      [
        ["#90c985", [{ condition: "state", entity: "sensor.dpc_roma_today_alert", state: "green" }]],
        ["#f8f865", [{ condition: "state", entity: "sensor.dpc_roma_today_alert", state: "yellow" }]],
        ["#f0bf01", [{ condition: "state", entity: "sensor.dpc_roma_today_alert", state: "orange" }]],
        ["#fd6767", [{ condition: "state", entity: "sensor.dpc_roma_today_alert", state: "red" }]],
        [
          undefined,
          [
            {
              condition: "state",
              entity: "sensor.dpc_roma_today_alert",
              state_not: ["green", "yellow", "orange", "red", "unknown", "unavailable"],
            },
          ],
        ],
      ],
    );
    assert.deepEqual(today[0].state_content, ["state", "risks"]);
    assert.deepEqual(today[0].name, { type: "entity" });
  });

  it("colors the criticality and the level of each risk by their level", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());

    const criticality = colorsOf(view, "sensor.dpc_roma_today_criticality");
    assert.equal(Object.keys(criticality).length, 10);
    assert.equal(criticality.absent, "#90c985");
    assert.equal(criticality.ordinary_thunderstorms, "#f8f865");
    assert.equal(criticality.moderate_hydrogeological, "#f0bf01");
    assert.equal(criticality.high_hydraulic, "#fd6767");
    assert.deepEqual(colorsOf(view, "sensor.dpc_roma_tomorrow_hydraulic_risk_level"), ALERT_COLORS);
  });

  it("shows a banner per risk on, in the color of its level", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());
    const banners = cardsFor(view, "binary_sensor.dpc_roma_tomorrow_hydrogeological_risk");

    // Visible in the state of the level of the same risk and day
    assert.deepEqual(
      banners.map((card) => [card.type, card.alert_color, card.visibility[1]]),
      Object.entries(ALERT_COLORS).map(([level, color]) => [
        "alert",
        color,
        {
          condition: "state",
          entity: "sensor.dpc_roma_tomorrow_hydrogeological_risk_level",
          state: level,
        },
      ]),
    );
    for (const banner of banners) {
      assert.deepEqual(banner.visibility[0], {
        condition: "state",
        entity: "binary_sensor.dpc_roma_tomorrow_hydrogeological_risk",
        state: "on",
      });
      assert.equal(banner.hide_state, true);
    }
  });

  it("shows a tile of a risk on whose level is disabled", () => {
    const hass = homeAssistant();
    delete hass.entities["sensor.dpc_roma_today_hydraulic_risk_level"];
    const view = generateView({ device_id: "roma" }, hass);

    assert.deepEqual(
      cardsFor(view, "binary_sensor.dpc_roma_today_hydraulic_risk").map((card) => [
        card.type,
        card.visibility,
      ]),
      [
        [
          "tile",
          [{ condition: "state", entity: "binary_sensor.dpc_roma_today_hydraulic_risk", state: "on" }],
        ],
      ],
    );
  });

  it("shows tiles of the risks on before Home Assistant has the alert card", () => {
    const hass = homeAssistant({ version: "2025.2.4" });
    const view = generateView({ device_id: "roma" }, hass);
    const risks = cardsOf(view).filter((card) => card.entity?.startsWith("binary_sensor."));

    assert.equal(risks.length, 6);
    for (const card of risks) {
      assert.equal(card.type, "tile");
      // Before 2025.11 tiles show the whole name of the entity
      assert.equal(card.name, undefined);
      assert.deepEqual(card.visibility, [{ condition: "state", entity: card.entity, state: "on" }]);
    }
  });

  it("shows the precipitation, the phenomena and the maps of each day", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());
    const [, today, tomorrow, afterTomorrow] = view.sections;

    assert.deepEqual(
      colorsOf(view, "sensor.dpc_roma_after_tomorrow_precipitation"),
      PRECIPITATION_COLORS,
    );
    // The number of phenomena has no color
    assert.deepEqual(
      cardsFor(view, "sensor.dpc_roma_today_nearby_phenomena").map((card) => card.color),
      [undefined],
    );
    // The phenomena of each day on the map of the day
    assert.deepEqual(today.cards.find((card) => card.type === "map").entities, [
      { entity: "geo_location.dpc_roma_today_isolated_thunderstorms_sse" },
    ]);
    assert.deepEqual(tomorrow.cards.find((card) => card.type === "map").entities, [
      { entity: "geo_location.dpc_roma_tomorrow_moderate_sea_sw" },
    ]);
    assert.equal(afterTomorrow.cards.find((card) => card.type === "map"), undefined);
    assert.deepEqual(
      today.cards.filter((card) => card.type === "picture-entity").map((card) => [
        card.entity,
        card.visibility,
      ]),
      [
        [
          "image.dpc_roma_today_criticality_map",
          [{ condition: "state", entity: "image.dpc_roma_today_criticality_map", state_not: ["unknown", "unavailable"] }],
        ],
        [
          "image.dpc_roma_today_vigilance_map",
          [{ condition: "state", entity: "image.dpc_roma_today_vigilance_map", state_not: ["unknown", "unavailable"] }],
        ],
      ],
    );
    // DPC publishes no map for the day after tomorrow
    assert.equal(afterTomorrow.cards.filter((card) => card.type === "picture-entity").length, 0);
  });

  it("shows the zones and bulletins of the place", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());
    const bulletins = view.sections.at(-1);

    assert.deepEqual(
      bulletins.cards.slice(1).map((card) => card.entity),
      [
        "sensor.dpc_roma_alert_zone",
        "sensor.dpc_roma_vigilance_zone",
        "sensor.dpc_roma_criticality_bulletin",
        "sensor.dpc_roma_vigilance_bulletin",
        "sensor.dpc_roma_criticality_valid_until",
        "sensor.dpc_roma_vigilance_valid_until",
      ],
    );
  });

  it("leaves out the cards of the entities that are disabled", () => {
    const hass = homeAssistant();
    for (const id of Object.keys(hass.entities)) {
      if (id.startsWith("image.") || id.endsWith("_zone")) delete hass.entities[id];
    }

    const view = generateView({ device_id: "roma" }, hass);

    assert.equal(cardsOf(view).filter((card) => card.type === "picture-entity").length, 0);
    assert.equal(cardsOf(view).filter((card) => card.entity?.endsWith("_zone")).length, 0);
  });

  it("titles the bulletins in the language of the user", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant({ language: "pt-BR" }));

    assert.equal(view.sections.at(-1).cards[0].heading, "Boletins");
  });

  it("asks for a place when the device is gone", () => {
    const view = generateView({ device_id: "gone" }, homeAssistant());

    assert.equal(view.cards[0].type, "markdown");
  });
});

describe("helpers", () => {
  it("compares versions of Home Assistant", () => {
    const hass = (version) => ({ config: { version } });
    assert.equal(isAtLeast(hass("2026.9.0"), [2026, 9]), true);
    assert.equal(isAtLeast(hass("2026.12.0.dev0"), [2026, 9]), true);
    assert.equal(isAtLeast(hass("2027.1.0"), [2026, 9]), true);
    assert.equal(isAtLeast(hass("2026.8.3"), [2026, 9]), false);
    assert.equal(isAtLeast(hass("2025.12.0"), [2026, 9]), false);
  });

  it("finds the texts of a language, its base language, or English", () => {
    assert.equal(textsIn("it").bulletins, "Bollettini");
    assert.equal(textsIn("it-CH").bulletins, "Bollettini");
    assert.equal(textsIn("pt").bulletins, "Boletins");
    assert.equal(textsIn("ja").bulletins, "Bulletins");
    assert.equal(textsIn(undefined).bulletins, "Bulletins");
  });

  it("localizes the dashboard creation suggestion", () => {
    assert.deepEqual(dashboardSuggestion("pt-BR"), {
      title: "Defesa Civil",
      icon: "mdi:shield-alert",
    });
    assert.deepEqual(dashboardSuggestion("it"), {
      title: "Dipartimento Protezione Civile",
      icon: "mdi:shield-alert",
    });
    assert.deepEqual(dashboardSuggestion("fr").title, "Département de la Protection civile");
    assert.deepEqual(dashboardSuggestion("de").title, "Zivilschutzabteilung");
    assert.deepEqual(dashboardSuggestion("es").title, "Departamento de Protección Civil");
    assert.deepEqual(dashboardSuggestion("en").title, "Civil Protection Department");
  });

  it("makes URL paths of names", () => {
    assert.equal(slugify("Città di Castello"), "citta-di-castello");
            state_not: ["green", "yellow", "orange", "red", "unknown", "unavailable"],
    assert.equal(slugify("—"), "dpc");
  });

  it("has the colors of DPC for the highest alert, as for the alert of a day", () => {
    assert.deepEqual(Object.values(HIGHEST_ALERT_COLORS), Object.values(ALERT_COLORS));
    assert.equal(CRITICALITY_COLORS.absent, ALERT_COLORS.green);
  });

  it("colors a card by state with a fallback for the other states", () => {
    const cards = colorByState({ type: "alert" }, "binary_sensor.x", { on: "red" }, "alert_color");

    assert.deepEqual(cards, [
      {
        type: "alert",
        alert_color: "red",
        visibility: [{ condition: "state", entity: "binary_sensor.x", state: "on" }],
      },
      {
        type: "alert",
        visibility: [
          {
            condition: "state",
            entity: "binary_sensor.x",
            state_not: ["on", "unknown", "unavailable"],
          },
        ],
      },
    ]);
  });
});
