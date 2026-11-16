// Tests of the DPC Alert dashboard strategy: node --test tests/frontend
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  colorByState,
  dashboardSuggestion,
  findPlaces,
  generateDashboard,
  generateView,
  isAtLeast,
  slugify,
  textsIn,
} from "../../custom_components/dpc/frontend/dpc-dashboard.js";

/** The days of a place, as the identifiers of their devices end and in entity IDs. */
const DAY_IDS = { today: "today", tomorrow: "tomorrow", aftertomorrow: "after_tomorrow" };

/** Return the devices of a DPC place: the place, and its days linked to it. */
function placeDevices(id, name) {
  return Object.fromEntries([
    [id, { id, name, identifiers: [["dpc", 41.9, 12.5]] }],
    ...Object.keys(DAY_IDS).map((day) => [
      `${id}-${day}`,
      {
        id: `${id}-${day}`,
        name: `${name} ${day}`,
        identifiers: [["dpc", `41.900000_12.500000-${day}`]],
        via_device_id: id,
      },
    ]),
  ]);
}

/** Return the registry entries of the entities of a DPC place and of its days. */
function placeEntities(device, prefix, phenomena = []) {
  const entity = (domain, key, day = null) => ({
    entity_id: day ? `${domain}.${prefix}_${DAY_IDS[day]}_${key}` : `${domain}.${prefix}_${key}`,
    platform: "dpc",
    device_id: day ? `${device}-${day}` : device,
    translation_key: key,
  });
  return [
    entity("sensor", "criticality"),
    entity("sensor", "vigilance"),
    ...["today", "tomorrow"].flatMap((day) => [
      entity("sensor", "alert", day),
      ...["hydraulic_risk", "thunderstorm_risk", "hydrogeological_risk"].map((key) =>
        entity("binary_sensor", key, day),
      ),
      entity("image", "criticality_map", day),
      entity("image", "vigilance_map", day),
    ]),
    ...Object.keys(DAY_IDS).map((day) => entity("sensor", "precipitation", day)),
    ...phenomena.map((category) => entity("geo_location", category, "today")),
  ];
}

/** Return a Home Assistant with the places Roma (with 2 phenomena) and Portula. */
function homeAssistant({ version = "2026.11.0", language = "en", entities = [] } = {}) {
  const all = [
    ...placeEntities("roma", "dpc_roma", ["precipitation", "sea"]),
    ...placeEntities("portula", "dpc_portula"),
    // Another integration on the same device is not shown
    { entity_id: "sensor.other", platform: "other", device_id: "roma" },
    ...entities,
  ];
  const portula = placeDevices("portula", "Portula");
  portula.portula.name_by_user = null;
  return {
    config: { version },
    locale: { language },
    devices: { ...placeDevices("roma", "Roma"), ...portula },
    entities: Object.fromEntries(all.map((entry) => [entry.entity_id, entry])),
  };
}

/** Return the cards of every section of a view. */
const cardsOf = (view) => view.sections.flatMap((section) => section.cards);

describe("dashboard", () => {
  it("has a view per place, sorted by name, built by the view strategy", () => {
    assert.deepEqual(generateDashboard(homeAssistant()).views, [
      {
        title: "Portula",
        path: "portula",
        icon: "mdi:shield-alert",
        strategy: { type: "custom:dpc-alert", device_id: "portula" },
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
    hass.devices.portula.name_by_user = "Peglio";
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
      ["Portula", "Roma"],
    );
  });

  it("finds the entities of a place on the devices of its days", () => {
    const [, roma] = findPlaces(homeAssistant());

    assert.equal(roma.entity("sensor", "criticality"), "sensor.dpc_roma_criticality");
    assert.equal(roma.entity("sensor", "alert", "tomorrow"), "sensor.dpc_roma_tomorrow_alert");
    assert.equal(roma.entity("sensor", "alert"), undefined);
    assert.equal(
      roma.entity("sensor", "precipitation", "aftertomorrow"),
      "sensor.dpc_roma_after_tomorrow_precipitation",
    );
  });

  it("leaves out a day whose place is gone", () => {
    const hass = homeAssistant();
    delete hass.devices.portula;

    assert.deepEqual(
      findPlaces(hass).map((place) => place.name),
      ["Roma"],
    );
  });
});

describe("view of a place", () => {
  it("shows the alert of each day in the color of its level", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());
    const today = cardsOf(view).filter((card) => card.entity === "sensor.dpc_roma_today_alert");

    assert.deepEqual(
      today.map((card) => [card.color, card.visibility]),
      [
        ["green", [{ condition: "state", entity: "sensor.dpc_roma_today_alert", state: "green" }]],
        ["yellow", [{ condition: "state", entity: "sensor.dpc_roma_today_alert", state: "yellow" }]],
        ["orange", [{ condition: "state", entity: "sensor.dpc_roma_today_alert", state: "orange" }]],
        ["red", [{ condition: "state", entity: "sensor.dpc_roma_today_alert", state: "red" }]],
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

  it("shows a banner per risk on, in the color of its level", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());
    const banners = cardsOf(view).filter(
      (card) => card.entity === "binary_sensor.dpc_roma_tomorrow_hydrogeological_risk",
    );

    assert.deepEqual(
      banners.map((card) => [card.type, card.alert_color, card.visibility[1]]),
      [1, 2, 3, 4].map((level, index) => [
        "alert",
        ["green", "yellow", "orange", "red"][index],
        {
          condition: "numeric_state",
          entity: "binary_sensor.dpc_roma_tomorrow_hydrogeological_risk",
          attribute: "level",
          above: level - 1,
          below: level + 1,
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

  it("shows the precipitation of each day, the phenomena and the maps", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant());
    const [, vigilance] = view.sections;

    const precipitation = vigilance.cards.filter(
      (card) => card.entity === "sensor.dpc_roma_after_tomorrow_precipitation",
    );
    assert.deepEqual(
      precipitation.map((card) => card.color),
      ["green", "light-blue", "blue", "indigo", "deep-purple", undefined],
    );
    const map = vigilance.cards.find((card) => card.type === "map");
    assert.deepEqual(map.entities, [
      { entity: "geo_location.dpc_roma_today_precipitation" },
      { entity: "geo_location.dpc_roma_today_sea" },
    ]);
    assert.deepEqual(
      vigilance.cards.filter((card) => card.type === "picture-entity").map((card) => card.entity),
      ["image.dpc_roma_today_vigilance_map", "image.dpc_roma_tomorrow_vigilance_map"],
    );
    assert.deepEqual(
      vigilance.cards.filter((card) => card.type === "picture-entity").map((card) => card.visibility),
      [
        [{ condition: "state", entity: "image.dpc_roma_today_vigilance_map", state_not: ["unknown", "unavailable"] }],
        [{ condition: "state", entity: "image.dpc_roma_tomorrow_vigilance_map", state_not: ["unknown", "unavailable"] }],
      ],
    );
  });

  it("has no map without phenomena near the place", () => {
    const view = generateView({ device_id: "portula" }, homeAssistant());

    assert.equal(cardsOf(view).filter((card) => card.type === "map").length, 0);
  });

  it("leaves out the cards of the entities that are disabled", () => {
    const hass = homeAssistant();
    for (const id of Object.keys(hass.entities)) {
      if (id.startsWith("image.")) delete hass.entities[id];
    }

    const view = generateView({ device_id: "roma" }, hass);

    assert.equal(cardsOf(view).filter((card) => card.type === "picture-entity").length, 0);
  });

  it("titles the sections in the language of the user", () => {
    const view = generateView({ device_id: "roma" }, homeAssistant({ language: "pt-BR" }));

    assert.deepEqual(
      view.sections.map((section) => section.cards[0].heading),
      ["Alertas", "Vigilância meteorológica"],
    );
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
    assert.equal(textsIn("it").criticality, "Allerte");
    assert.equal(textsIn("it-CH").criticality, "Allerte");
    assert.equal(textsIn("pt").vigilance, "Vigilância meteorológica");
    assert.equal(textsIn("ja").criticality, "Alerts");
    assert.equal(textsIn(undefined).criticality, "Alerts");
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
