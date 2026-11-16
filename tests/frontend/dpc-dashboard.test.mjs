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
  dayName,
  entityName,
  findPlaces,
  generateDashboard,
  generateView,
  isAtLeast,
  slugify,
  textsIn,
  translated,
  withTexts,
} from "../../custom_components/dpc/frontend/dpc-dashboard.js";
import { homeAssistant, placeDevices, placeEntities } from "./fixtures.mjs";

/** The texts of the integration in Portuguese, some of them. */
const PORTUGUESE = {
  "component.dpc.entity.sensor.precipitation.name": "Precipitação",
  "component.dpc.entity.image.criticality_map.name": "Mapa de criticidade",
  "component.dpc.entity.binary_sensor.hydraulic_risk.name": "Risco hidráulico",
  "component.dpc.device.today.name": "{place} · Hoje",
};

/**
 * Return a Home Assistant whose frontend loads the texts of the integration
 * in Portuguese: the entities first, then the devices.
 */
function portuguese(hass) {
  const loaded = [];
  const localize = (key, values = {}) =>
    loaded.includes("device") || !key.includes(".device.")
      ? (PORTUGUESE[key] ?? "").replace(/\{(\w+)\}/g, (_, name) => values[name])
      : "";
  return {
    ...hass,
    loadBackendTranslation: async (category, integration) => {
      assert.equal(integration, "dpc");
      loaded.push(category);
      return localize;
    },
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
  it("has a view per place, sorted by name, its tab named after it", () => {
    assert.deepEqual(generateDashboard(homeAssistant()).views, [
      {
        title: "Milano",
        path: "milano",
        strategy: { type: "custom:dpc-alert", device_id: "milano" },
      },
      {
        title: "Roma",
        path: "roma",
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
  it("has a section for the place and one for each of its days", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());

    assert.equal(view.type, "sections");
    // The days as their devices name them, without the place
    assert.deepEqual(
      view.sections.map((section) => section.cards[0].heading),
      ["Roma", "Today", "Tomorrow", "Day after tomorrow"],
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
      ["Roma", "Today", "Day after tomorrow"],
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
      // No precipitation in the color of the icons of the theme, rather than white
      1: "var(--state-icon-color)",
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

  it("always shows the tile of a risk whose level is disabled", () => {
    const hass = homeAssistant();
    delete hass.entities["sensor.dpc_roma_today_hydraulic_risk_level"];
    const view = generateView({ device_id: "roma" }, hass);

    // The risk is all the dashboard has of it, whether it is on or off
    assert.deepEqual(cardsFor(view, "binary_sensor.dpc_roma_today_hydraulic_risk"), [
      {
        type: "tile",
        entity: "binary_sensor.dpc_roma_today_hydraulic_risk",
        name: { type: "entity" },
        grid_options: { columns: 4 },
      },
    ]);
  });

  it("shows the risks of a place that shows only them", () => {
    const hass = homeAssistant();
    for (const [id, entry] of Object.entries(hass.entities)) {
      if (!id.startsWith("binary_sensor.") || entry.device_id !== "roma-today") {
        delete hass.entities[id];
      }
    }
    const view = generateView({ device_id: "roma" }, hass);

    // The place, without its sensors, has nothing to show: no section
    assert.deepEqual(
      view.sections.map((section) => section.cards.map((card) => card.heading ?? card.entity)),
      [
        [
          "Today",
          "binary_sensor.dpc_roma_today_hydraulic_risk",
          "binary_sensor.dpc_roma_today_thunderstorm_risk",
          "binary_sensor.dpc_roma_today_hydrogeological_risk",
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
      { entity: "geo_location.dpc_roma_today_isolated_thunderstorms_sse", label_mode: "icon" },
    ]);
    assert.deepEqual(tomorrow.cards.find((card) => card.type === "map").entities, [
      { entity: "geo_location.dpc_roma_tomorrow_moderate_sea_sw", label_mode: "icon" },
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

  it("shows the zones and bulletins in the section of the place", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());
    const [place] = view.sections;

    assert.deepEqual(
      place.cards.filter((card) => card.type === "tile" && !card.visibility).map((card) => card.entity),
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

  it("shows the maps of a day right after the cards as wide as the section", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());
    const today = view.sections[1];
    const order = [...new Set(today.cards.map((card) => card.entity ?? card.type))];

    assert.deepEqual(order.slice(order.indexOf("sensor.dpc_roma_today_criticality")), [
      "sensor.dpc_roma_today_criticality",
      "image.dpc_roma_today_criticality_map",
      "image.dpc_roma_today_vigilance_map",
      "map",
      "sensor.dpc_roma_today_hydraulic_risk_level",
      "sensor.dpc_roma_today_thunderstorm_risk_level",
      "sensor.dpc_roma_today_hydrogeological_risk_level",
      "sensor.dpc_roma_today_precipitation",
      "sensor.dpc_roma_today_nearby_phenomena",
    ]);
  });

  it("names the days and the entities in the language of the user", async () => {
    const hass = await withTexts(portuguese(homeAssistant()));
    const view = generateView({ device_id: "roma" }, hass);
    const [, today] = view.sections;

    assert.equal(today.cards[0].heading, "Hoje");
    assert.equal(cardsFor(view, "sensor.dpc_roma_today_precipitation")[0].name, "Precipitação");
    assert.equal(
      cardsFor(view, "image.dpc_roma_today_criticality_map")[0].name,
      "Mapa de criticidade",
    );
    assert.equal(
      cardsFor(view, "binary_sensor.dpc_roma_today_hydraulic_risk")[0].name,
      "Risco hidráulico",
    );
    // Without a text, as Home Assistant names the entity
    assert.deepEqual(cardsFor(view, "sensor.dpc_roma_today_alert")[0].name, { type: "entity" });
    assert.equal(cardsFor(view, "image.dpc_roma_today_vigilance_map")[0].name, undefined);
  });

  it("keeps the name the user gave a day", async () => {
    const hass = await withTexts(portuguese(homeAssistant()));
    hass.devices["roma-tomorrow"].name_by_user = "Roma · Domani";

    assert.equal(dayName(hass, findPlaces(hass)[1], "tomorrow"), "Domani");
    // A text of a day without the place is taken whole
    const other = { ...hass, localize: () => "Amanhã" };
    assert.equal(dayName(other, findPlaces(other)[1], "today"), "Amanhã");
  });

  it("names as Home Assistant does without the texts of the integration", async () => {
    const hass = homeAssistant();
    assert.equal(await withTexts(hass), hass);
    assert.equal(entityName(hass, "sensor.dpc_roma_today_precipitation"), undefined);
    assert.equal(entityName(hass, "sensor.not_in_the_registry"), undefined);
    assert.equal(translated(hass, "device.today.name"), undefined);
    assert.equal(dayName(hass, findPlaces(hass)[1], "today"), "Today");
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
    // Chinese in any script or region: the simplified texts
    assert.equal(textsIn("zh-Hant").bulletins, "公报");
    assert.equal(textsIn("uk").bulletins, "Бюлетені");
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
    assert.deepEqual(dashboardSuggestion("ar").title, "إدارة الحماية المدنية");
    assert.deepEqual(dashboardSuggestion("hi").title, "नागरिक सुरक्षा विभाग");
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
