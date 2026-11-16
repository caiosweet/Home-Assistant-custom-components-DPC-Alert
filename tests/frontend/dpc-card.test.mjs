// Tests of the DPC Alert card: node --test tests/frontend
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  BULLETIN_ITEMS,
  CARDS,
  alertLayout,
  bulletinLayout,
  cardLayout,
  cardModel,
  checkConfig,
  cleanConfig,
  editorData,
  editorSchema,
  headingOptions,
  mapLayout,
  placeLayout,
  placeOf,
  swatch,
} from "../../custom_components/dpc/frontend/dpc-card.js";
import { findPlaces } from "../../custom_components/dpc/frontend/dpc-dashboard.js";
import { homeAssistant } from "./fixtures.mjs";

/** Return the states of entities, as Home Assistant has them. */
const statesOf = (states) =>
  Object.fromEntries(
    Object.entries(states).map(([entity_id, state]) => [entity_id, { entity_id, state }]),
  );

/** Milano: an orange alert and light rain today, heavy rain after tomorrow. */
const MILANO = statesOf({
  "sensor.dpc_milano_highest_alert": "3",
  "sensor.dpc_milano_highest_precipitation": "4",
  "sensor.dpc_milano_today_alert": "orange",
  "sensor.dpc_milano_today_precipitation": "light",
  "sensor.dpc_milano_tomorrow_alert": "green",
  "sensor.dpc_milano_tomorrow_precipitation": "moderate",
  "sensor.dpc_milano_after_tomorrow_precipitation": "heavy",
});

/** The texts of the integration a frontend in Portuguese has. */
const PORTUGUESE = {
  "component.dpc.entity.sensor.precipitation.name": "Precipitação",
  "component.dpc.device.today.name": "{place} · Hoje",
  "component.dpc.device.tomorrow.name": "{place} · Amanhã",
  "component.dpc.device.aftertomorrow.name": "{place} · Depois de amanhã",
};

/** Return a localize of the frontend with texts, which says "" for the others. */
const localizeWith =
  (texts) =>
  (key, values = {}) =>
    (texts[key] ?? "").replace(/\{(\w+)\}/g, (_, name) => values[name]);

/** Return a Home Assistant with the states of Milano. */
const withStates = (options = {}, states = MILANO) => ({ ...homeAssistant(options), states });

/** Return the place Milano of a Home Assistant. */
const milano = (hass) => placeOf(findPlaces(hass), { device_id: "milano" });

/** Return the native cards of Milano, as the card places them. */
const milanoLayout = (hass) => placeLayout(hass, cardModel(hass, milano(hass)));

describe("card", () => {
  it("shows the place of its device", () => {
    const places = findPlaces(homeAssistant());
    assert.equal(placeOf(places, { device_id: "roma" })?.name, "Roma");
  });

  it("shows the first place without a device", () => {
    const places = findPlaces(homeAssistant());
    assert.equal(placeOf(places, {})?.name, "Milano");
  });

  it("shows no place for a device that is not a place", () => {
    const places = findPlaces(homeAssistant());
    assert.equal(placeOf(places, { device_id: "removed" }), undefined);
    assert.equal(placeOf([], {}), undefined);
  });

  it("colors the highest alert and precipitation of the place", () => {
    const hass = withStates();
    const model = cardModel(hass, milano(hass));
    assert.equal(model.name, "Milano");
    assert.deepEqual(model.highestAlert, {
      entity: "sensor.dpc_milano_highest_alert",
      color: "#f0bf01",
    });
    assert.deepEqual(model.highestPrecipitation, {
      entity: "sensor.dpc_milano_highest_precipitation",
      color: "#f0bf01",
    });
  });

  it("shows the alert and the precipitation of each day, in the DPC colors", () => {
    const hass = withStates();
    const days = cardModel(hass, milano(hass)).days;
    assert.deepEqual(
      days.map(({ day, name, alert, precipitation }) => [
        day,
        name,
        alert?.color,
        precipitation?.color,
      ]),
      [
        ["today", "Today", "#f0bf01", "#90c985"],
        ["tomorrow", "Tomorrow", "#90c985", "#f8f865"],
        // Only the vigilance bulletin covers the day after tomorrow
        ["aftertomorrow", "Day after tomorrow", undefined, "#f0bf01"],
      ],
    );
    assert.equal(days[2].alert, undefined);
  });

  it("shows no precipitation in the color of the icons of the theme, rather than white", () => {
    const hass = withStates(
      {},
      statesOf({
        "sensor.dpc_milano_highest_precipitation": "1",
        "sensor.dpc_milano_today_precipitation": "none",
      }),
    );
    const model = cardModel(hass, milano(hass));
    assert.equal(model.highestPrecipitation?.color, "var(--state-icon-color)");
    assert.equal(model.days[0].precipitation?.color, "var(--state-icon-color)");
  });

  it("has no color without data", () => {
    const hass = withStates({}, statesOf({ "sensor.dpc_milano_today_alert": "unavailable" }));
    const [today] = cardModel(hass, milano(hass)).days;
    assert.deepEqual(today.alert, { entity: "sensor.dpc_milano_today_alert", color: undefined });
    assert.deepEqual(today.precipitation, {
      entity: "sensor.dpc_milano_today_precipitation",
      color: undefined,
    });
    assert.equal(swatch(hass.states, undefined, {}), undefined);
  });

  it("names the days and the precipitation in the language of the user", () => {
    const hass = { ...withStates(), localize: localizeWith(PORTUGUESE) };
    const tiles = milanoLayout(hass).slice(1);
    assert.deepEqual(
      tiles.map(({ card }) => card.name),
      ["Hoje", "Precipitação", "Amanhã", "Precipitação", "Depois de amanhã"],
    );
  });

  it("is made of native cards: a heading, and the tiles of each day in their column", () => {
    assert.deepEqual(milanoLayout(withStates()), [
      {
        card: {
          type: "heading",
          heading: "Milano",
          icon: "mdi:shield-alert",
          badges: [
            { type: "entity", entity: "sensor.dpc_milano_highest_alert", color: "#f0bf01" },
            {
              type: "entity",
              entity: "sensor.dpc_milano_highest_precipitation",
              color: "#f0bf01",
            },
          ],
        },
        column: "all",
      },
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_today_alert",
          name: "Today",
          color: "#f0bf01",
        },
        column: "start",
      },
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_today_precipitation",
          name: { type: "entity" },
          color: "#90c985",
        },
        column: "end",
      },
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_tomorrow_alert",
          name: "Tomorrow",
          color: "#90c985",
        },
        column: "start",
      },
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_tomorrow_precipitation",
          name: { type: "entity" },
          color: "#f8f865",
        },
        column: "end",
      },
      // Without an alert, the precipitation keeps its column, named after the day
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_after_tomorrow_precipitation",
          name: "Day after tomorrow",
          color: "#f0bf01",
        },
        column: "end",
      },
    ]);
  });

  it("leaves the color of the theme to states without data", () => {
    const [heading, alert] = milanoLayout(withStates({}, {}));
    assert.deepEqual(heading.card.badges, [
      { type: "entity", entity: "sensor.dpc_milano_highest_alert" },
      { type: "entity", entity: "sensor.dpc_milano_highest_precipitation" },
    ]);
    assert.equal(alert.card.color, undefined);
  });

  it("names the precipitation with its whole name before Home Assistant 2025.11", () => {
    const [, , precipitation] = milanoLayout(withStates({ version: "2025.10.0" }));
    assert.equal(precipitation.card.name, undefined);
  });

  it("has no tiles for a day without its entities", () => {
    const hass = withStates();
    const place = milano(hass);
    place.entries = place.entries.filter(({ day }) => day !== "tomorrow");
    const tiles = placeLayout(hass, cardModel(hass, place)).slice(1);
    assert.deepEqual(
      tiles.map(({ card }) => card.entity),
      [
        "sensor.dpc_milano_today_alert",
        "sensor.dpc_milano_today_precipitation",
        "sensor.dpc_milano_after_tomorrow_precipitation",
      ],
    );
  });

  it("asks for a place when there is none", () => {
    const hass = withStates({ language: "it" });
    assert.deepEqual(cardLayout(alertLayout, hass, [], {}), [
      {
        card: {
          type: "markdown",
          content:
            "Aggiungi un luogo dell'integrazione Dipartimento Protezione Civile per vederne qui le allerte.",
        },
        column: "all",
      },
    ]);
  });

  it("heads the card with the place of its device", () => {
    const hass = withStates();
    const [heading] = cardLayout(alertLayout, hass, findPlaces(hass), { device_id: "roma" });
    assert.equal(heading.card.heading, "Roma");
  });
});

/** Milano with its bulletins: the zones, the publications, the validity. */
const BULLETINS = statesOf({
  "sensor.dpc_milano_alert_zone": "Lomb-11",
  "sensor.dpc_milano_vigilance_zone": "Lombardia 5",
  "sensor.dpc_milano_criticality_bulletin": "2026-11-16T14:00:00+00:00",
  "sensor.dpc_milano_vigilance_bulletin": "2026-11-16T13:00:00+00:00",
  "sensor.dpc_milano_criticality_valid_until": "2026-11-17T23:00:00+00:00",
  "sensor.dpc_milano_vigilance_valid_until": "2026-11-18T23:00:00+00:00",
});

describe("bulletin card", () => {
  it("shows the criticality bulletin and, beside it, the vigilance bulletin", () => {
    const hass = withStates({}, BULLETINS);
    const [title, ...tiles] = bulletinLayout(hass, milano(hass), {});
    assert.equal(title.card.heading, "Milano");
    assert.deepEqual(title.card.badges, []);
    assert.deepEqual(
      tiles.map(({ card, column }) => [card.entity, column]),
      [
        ["sensor.dpc_milano_alert_zone", "start"],
        ["sensor.dpc_milano_vigilance_zone", "end"],
        ["sensor.dpc_milano_criticality_bulletin", "start"],
        ["sensor.dpc_milano_vigilance_bulletin", "end"],
        ["sensor.dpc_milano_criticality_valid_until", "start"],
        ["sensor.dpc_milano_vigilance_valid_until", "end"],
      ],
    );
  });

  it("names the data of the bulletins in the language of the user", () => {
    const hass = {
      ...withStates({}, BULLETINS),
      localize: localizeWith({
        "component.dpc.entity.sensor.alert_zone.name": "Zona de alerta",
      }),
    };
    const [, zone, vigilance] = bulletinLayout(hass, milano(hass), {});
    assert.equal(zone.card.name, "Zona de alerta");
    // Without the text, as the dashboard names it
    assert.deepEqual(vigilance.card.name, { type: "entity" });
  });

  it("shows only the data of the enabled entities", () => {
    const hass = withStates({}, BULLETINS);
    const place = milano(hass);
    place.entries = place.entries.filter(({ entry }) => entry.translation_key !== "alert_zone");
    const [, first] = bulletinLayout(hass, place, {});
    assert.deepEqual([first.card.entity, first.column], ["sensor.dpc_milano_vigilance_zone", "end"]);
  });
});

/** Milano with the maps of today and tomorrow, and the levels of each day. */
const MAPS = statesOf({
  ...Object.fromEntries(Object.entries(MILANO).map(([entity, { state }]) => [entity, state])),
  "image.dpc_milano_today_criticality_map": "2026-11-16T14:00:00+00:00",
  "image.dpc_milano_tomorrow_criticality_map": "2026-11-16T14:00:00+00:00",
  "image.dpc_milano_today_vigilance_map": "2026-11-16T13:00:00+00:00",
  // No vigilance map for tomorrow yet
  "image.dpc_milano_tomorrow_vigilance_map": "unknown",
});

describe("map card", () => {
  it("shows the map of today, and beside it a block for each day with a map", () => {
    const hass = withStates({}, MAPS);
    assert.deepEqual(mapLayout(hass, milano(hass), {}), [
      {
        card: {
          type: "heading",
          heading: "Milano",
          icon: "mdi:shield-alert",
          badges: [
            { type: "entity", entity: "sensor.dpc_milano_highest_alert", color: "#f0bf01" },
          ],
        },
        column: "all",
      },
      {
        card: {
          type: "picture-entity",
          entity: "image.dpc_milano_today_criticality_map",
          show_name: false,
          show_state: false,
        },
        column: "start",
        rows: 2,
      },
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_today_alert",
          name: "Today",
          tap_action: { action: "none" },
          icon_tap_action: { action: "none" },
          color: "#f0bf01",
        },
        column: "end",
        select: "today",
        selected: true,
      },
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_tomorrow_alert",
          name: "Tomorrow",
          tap_action: { action: "none" },
          icon_tap_action: { action: "none" },
          color: "#90c985",
        },
        column: "end",
        select: "tomorrow",
        selected: false,
      },
    ]);
  });

  it("shows the map of the day selected", () => {
    const hass = withStates({}, MAPS);
    const [, map, today, tomorrow] = mapLayout(hass, milano(hass), {}, "tomorrow");
    assert.equal(map.card.entity, "image.dpc_milano_tomorrow_criticality_map");
    assert.deepEqual([today.selected, tomorrow.selected], [false, true]);
  });

  it("shows the vigilance map, with the precipitation of the days that have one", () => {
    const hass = withStates({}, MAPS);
    // Tomorrow selected, but without its map: the first day with one instead
    const [title, map, ...blocks] = mapLayout(
      hass,
      milano(hass),
      { map: "vigilance" },
      "tomorrow",
    );
    assert.deepEqual(title.card.badges, [
      { type: "entity", entity: "sensor.dpc_milano_highest_precipitation", color: "#f0bf01" },
    ]);
    assert.equal(map.card.entity, "image.dpc_milano_today_vigilance_map");
    assert.equal(map.rows, 1);
    assert.deepEqual(
      blocks.map(({ card }) => [card.entity, card.color]),
      [["sensor.dpc_milano_today_precipitation", "#90c985"]],
    );
  });

  it("shows only the heading without a map", () => {
    const hass = withStates();
    assert.deepEqual(
      mapLayout(hass, milano(hass), {}).map(({ card }) => card.type),
      ["heading"],
    );
  });

  it("has no block for a day without its sensor", () => {
    const hass = withStates({}, MAPS);
    const place = milano(hass);
    place.entries = place.entries.filter(
      ({ entry, day }) => !(day === "tomorrow" && entry.translation_key === "alert"),
    );
    const [, map, ...blocks] = mapLayout(hass, place, {});
    assert.equal(map.rows, 2);
    assert.deepEqual(
      blocks.map(({ select }) => select),
      ["today"],
    );
  });
});

describe("cards", () => {
  it("are three, each in the card picker", () => {
    assert.deepEqual(
      CARDS.map(({ type }) => type),
      ["dpc-card", "dpc-bulletin-card", "dpc-map-card"],
    );
    const texts = { bulletins: "Boletins", maps: "Mapas" };
    assert.deepEqual(
      CARDS.map(({ name }) => name(texts)),
      ["DPC Alert", "DPC Alert · Boletins", "DPC Alert · Mapas"],
    );
  });

  it("check their configuration", () => {
    checkConfig({});
    checkConfig({ device_id: "milano", map: "vigilance" });
    assert.throws(() => checkConfig({ device_id: 1 }), /device_id/);
    assert.throws(() => checkConfig({ map: "radar" }), /map must be one of: criticality, vigilance/);
  });

  it("show a message without places, whatever the card", () => {
    const hass = withStates();
    for (const { layout } of CARDS) {
      assert.equal(cardLayout(layout, hass, [], {})[0].card.type, "markdown");
    }
  });
});

/** Return the entity and the column of each native card but the heading. */
const placesOf = (layout) =>
  layout.filter(({ card }) => card.type !== "heading").map(({ card, column }) => [card.entity, column]);

describe("options of the cards", () => {
  it("show the badges without the title, and no heading without either", () => {
    const hass = withStates();
    const [heading] = alertLayout(hass, milano(hass), { show_title: false });
    assert.deepEqual(heading.card.heading, "");
    assert.equal(heading.card.icon, undefined);
    assert.equal(heading.card.badges.length, 2);

    const layout = alertLayout(hass, milano(hass), {
      show_title: false,
      show_highest_alert: false,
      show_highest_precipitation: false,
    });
    assert.equal(layout.some(({ card }) => card.type === "heading"), false);
  });

  it("show only the highest level chosen", () => {
    const hass = withStates();
    const [heading] = alertLayout(hass, milano(hass), { show_highest_alert: false });
    assert.deepEqual(
      heading.card.badges.map((badge) => badge.entity),
      ["sensor.dpc_milano_highest_precipitation"],
    );
  });

  it("show only the days chosen, in a single column one below the other", () => {
    const hass = withStates();
    const layout = alertLayout(hass, milano(hass), { days: ["aftertomorrow", "today"], columns: 1 });
    assert.deepEqual(placesOf(layout), [
      ["sensor.dpc_milano_today_alert", "all"],
      ["sensor.dpc_milano_today_precipitation", "all"],
      ["sensor.dpc_milano_after_tomorrow_precipitation", "all"],
    ]);
  });

  it("show only the data of the bulletins chosen, side by side", () => {
    const hass = withStates({}, BULLETINS);
    const layout = bulletinLayout(hass, milano(hass), {
      items: ["vigilance_zone", "criticality_bulletin", "vigilance_valid_until"],
      show_title: false,
    });
    assert.deepEqual(placesOf(layout), [
      // Alone in its row, the vigilance datum keeps its column
      ["sensor.dpc_milano_vigilance_zone", "end"],
      ["sensor.dpc_milano_criticality_bulletin", "start"],
      ["sensor.dpc_milano_vigilance_valid_until", "end"],
    ]);
    assert.equal(layout.length, 3);
  });

  it("show the criticality bulletin first in a single column", () => {
    const hass = withStates({}, BULLETINS);
    assert.deepEqual(
      placesOf(bulletinLayout(hass, milano(hass), { columns: 1 })).map(([entity]) => entity),
      BULLETIN_ITEMS.map((key) => `sensor.dpc_milano_${key}`),
    );
  });

  it("show the maps of the days chosen, with or without the highest level", () => {
    const hass = withStates({}, MAPS);
    const [heading, map, ...blocks] = mapLayout(hass, milano(hass), {
      days: ["tomorrow"],
      show_highest_alert: false,
    });
    assert.deepEqual(heading.card.badges, []);
    assert.equal(map.card.entity, "image.dpc_milano_tomorrow_criticality_map");
    assert.deepEqual(
      blocks.map(({ select }) => select),
      ["tomorrow"],
    );

    const [vigilance] = mapLayout(hass, milano(hass), {
      map: "vigilance",
      show_highest_alert: false,
    });
    // The highest level of the vigilance map is its precipitation
    assert.equal(vigilance.card.badges.length, 1);
  });

  it("have the width of their columns", () => {
    const columns = Object.fromEntries(CARDS.map(({ type, columns }) => [type, [columns({}), columns({ columns: 1 })]]));
    assert.deepEqual(columns, {
      "dpc-card": ["minmax(0, 2fr) minmax(0, 3fr)", "minmax(0, 1fr)"],
      "dpc-bulletin-card": ["minmax(0, 1fr) minmax(0, 1fr)", "minmax(0, 1fr)"],
      "dpc-map-card": ["minmax(0, 1fr) minmax(0, 1fr)", "minmax(0, 1fr) minmax(0, 1fr)"],
    });
  });

  it("are checked", () => {
    checkConfig({
      show_title: false,
      show_highest_alert: true,
      days: ["today"],
      items: [],
      columns: 1,
    });
    assert.throws(() => checkConfig({ show_title: "no" }), /show_title must be true or false/);
    assert.throws(() => checkConfig({ days: ["yesterday"] }), /days must be a list of: today, tomorrow, aftertomorrow/);
    assert.throws(() => checkConfig({ days: "today" }), /days must be a list/);
    assert.throws(() => checkConfig({ items: ["link"] }), /items must be a list of: alert_zone/);
    assert.throws(() => checkConfig({ columns: 3 }), /columns must be 1 or 2/);
  });
});

describe("visual editor", () => {
  /** The texts of the integration in Portuguese the editor uses. */
  const texts = {
    "component.dpc.device.today.name": "{place} · Hoje",
    "component.dpc.device.tomorrow.name": "{place} · Amanhã",
    "component.dpc.entity.sensor.highest_alert.name": "Alerta máximo",
    "component.dpc.entity.sensor.highest_precipitation.name": "Precipitação máxima",
    "component.dpc.entity.sensor.alert_zone.name": "Zona de alerta",
    "component.dpc.entity.image.criticality_map.name": "Mapa de criticidade",
  };
  const portuguese = () => ({
    ...withStates({ language: "pt-BR" }),
    localize: localizeWith(texts),
  });

  it("has the fields of each card, labeled in the language of the user", () => {
    const hass = portuguese();
    const places = findPlaces(hass);
    const fields = (type, config = {}) =>
      editorSchema(type, hass, places, config).map(({ name, label }) => [name, label]);

    assert.deepEqual(fields("dpc-card"), [
      ["device_id", "Lugar"],
      ["heading", "Cabeçalho"],
      ["days", "Dias"],
      ["columns", "Colunas"],
    ]);
    assert.deepEqual(fields("dpc-bulletin-card"), [
      ["device_id", "Lugar"],
      ["heading", "Cabeçalho"],
      ["items", "Boletins"],
      ["columns", "Colunas"],
    ]);
    assert.deepEqual(fields("dpc-map-card"), [
      ["device_id", "Lugar"],
      ["map", "Mapas"],
      ["heading", "Cabeçalho"],
      ["days", "Dias"],
    ]);
  });

  it("lists what the heading shows, as compact as the days", () => {
    const hass = portuguese();
    const places = findPlaces(hass);
    const heading = (type, config = {}) =>
      editorSchema(type, hass, places, config).find((field) => field.name === "heading").selector
        .select;

    assert.deepEqual(heading("dpc-card"), {
      multiple: true,
      mode: "list",
      options: [
        { value: "show_title", label: "Título" },
        { value: "show_highest_alert", label: "Alerta máximo" },
        { value: "show_highest_precipitation", label: "Precipitação máxima" },
      ],
    });
    assert.deepEqual(heading("dpc-bulletin-card").options, [{ value: "show_title", label: "Título" }]);
    // The highest level of the map card is that of its map
    assert.deepEqual(heading("dpc-map-card").options[1], {
      value: "show_highest",
      label: "Alerta máximo",
    });
    assert.deepEqual(heading("dpc-map-card", { map: "vigilance" }).options[1], {
      value: "show_highest",
      label: "Precipitação máxima",
    });
    assert.deepEqual(headingOptions("dpc-map-card", "vigilance"), {
      show_title: "show_title",
      show_highest: "show_highest_precipitation",
    });
  });

  it("offers the places, the days and the data of the bulletins by name", () => {
    const hass = portuguese();
    const places = findPlaces(hass);
    const options = (type, name) =>
      editorSchema(type, hass, places, {}).find((field) => field.name === name).selector.select
        .options;

    assert.deepEqual(options("dpc-card", "device_id"), [
      { value: "milano", label: "Milano" },
      { value: "roma", label: "Roma" },
    ]);
    // Without a text, the key of the day
    assert.deepEqual(
      options("dpc-card", "days").map(({ label }) => label),
      ["Hoje", "Amanhã", "aftertomorrow"],
    );
    assert.deepEqual(options("dpc-bulletin-card", "items")[0], {
      value: "alert_zone",
      label: "Zona de alerta",
    });
    assert.deepEqual(options("dpc-bulletin-card", "items")[1].label, "criticality_bulletin");
    assert.deepEqual(options("dpc-map-card", "map")[0], {
      value: "criticality",
      label: "Mapa de criticidade",
    });
  });

  it("keeps a place that is gone, by its ID", () => {
    const hass = portuguese();
    const [, ...gone] = editorSchema("dpc-card", hass, findPlaces(hass), { device_id: "gone" })[0]
      .selector.select.options;
    assert.deepEqual(gone.at(-1), { value: "gone", label: "gone" });
  });

  it("starts from what the card shows", () => {
    const places = findPlaces(withStates());
    assert.deepEqual(editorData("dpc-map-card", places, { type: "custom:dpc-map-card" }), {
      type: "custom:dpc-map-card",
      device_id: "milano",
      show_title: true,
      show_highest_alert: true,
      show_highest_precipitation: true,
      heading: ["show_title", "show_highest"],
      days: ["today", "tomorrow"],
      items: BULLETIN_ITEMS,
      columns: "2",
      map: "criticality",
    });
    assert.equal(editorData("dpc-card", places, { columns: 1 }).columns, "1");
    assert.deepEqual(
      editorData("dpc-card", places, { show_title: false, show_highest_alert: false }).heading,
      ["show_highest_precipitation"],
    );
  });

  it("keeps in the configuration only what differs from what the card shows anyway", () => {
    const data = editorData("dpc-card", findPlaces(withStates()), { type: "custom:dpc-card" });
    assert.deepEqual(cleanConfig("dpc-card", data), {
      type: "custom:dpc-card",
      device_id: "milano",
    });
    assert.deepEqual(
      cleanConfig("dpc-card", {
        ...data,
        heading: ["show_highest_alert", "show_highest_precipitation"],
        days: ["tomorrow", "today"],
        columns: "1",
      }),
      {
        type: "custom:dpc-card",
        device_id: "milano",
        show_title: false,
        days: ["today", "tomorrow"],
        columns: 1,
      },
    );
    // The highest level of the map card stays checked when its map changes
    assert.deepEqual(
      cleanConfig("dpc-map-card", {
        map: "vigilance",
        show_highest_alert: false,
        heading: ["show_highest"],
      }),
      { map: "vigilance", show_title: false, show_highest_alert: false },
    );
    assert.deepEqual(
      cleanConfig("dpc-bulletin-card", { items: ["vigilance_zone", "alert_zone"] }),
      { items: ["alert_zone", "vigilance_zone"] },
    );
    // All the days of the map card are those it has maps of
    assert.deepEqual(cleanConfig("dpc-map-card", { days: ["tomorrow", "today"] }), {});
  });
});

