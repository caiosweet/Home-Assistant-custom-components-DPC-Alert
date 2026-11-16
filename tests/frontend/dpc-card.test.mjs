// Tests of the DPC Alert card: node --test tests/frontend
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  CARDS,
  alertLayout,
  bulletinLayout,
  cardLayout,
  cardModel,
  checkConfig,
  dayName,
  mapLayout,
  placeLayout,
  placeOf,
  swatch,
  translated,
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
      color: "#508BFF",
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
        ["today", "Today", "#f0bf01", "#C3FFFE"],
        ["tomorrow", "Tomorrow", "#90c985", "#50FFFF"],
        // Only the vigilance bulletin covers the day after tomorrow
        ["aftertomorrow", "Day after tomorrow", undefined, "#508BFF"],
      ],
    );
    assert.equal(days[2].alert, undefined);
  });

  it("leaves no precipitation in the color of the theme, rather than white", () => {
    const hass = withStates(
      {},
      statesOf({
        "sensor.dpc_milano_highest_precipitation": "1",
        "sensor.dpc_milano_today_precipitation": "none",
      }),
    );
    const model = cardModel(hass, milano(hass));
    assert.equal(model.highestPrecipitation?.color, undefined);
    assert.equal(model.days[0].precipitation?.color, undefined);
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

  it("keeps the name the user gave a day", () => {
    const hass = { ...withStates(), localize: localizeWith(PORTUGUESE) };
    hass.devices["milano-today"].name_by_user = "Milano · Oggi";
    assert.equal(dayName(hass, milano(hass), "today"), "Oggi");
  });

  it("names a day as its device without the texts of the integration", () => {
    const hass = { ...withStates(), localize: localizeWith({}) };
    assert.equal(dayName(hass, milano(hass), "tomorrow"), "Tomorrow");
    assert.equal(translated(hass, "entity.sensor.precipitation.name"), undefined);
    // A translation that does not start with the place is kept whole
    const other = { ...hass, localize: () => "Domani" };
    assert.equal(dayName(other, milano(other), "tomorrow"), "Domani");
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
              color: "#508BFF",
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
          color: "#C3FFFE",
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
          color: "#50FFFF",
        },
        column: "end",
      },
      // Without an alert, the precipitation keeps its column, named after the day
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_after_tomorrow_precipitation",
          name: "Day after tomorrow",
          color: "#508BFF",
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
      { type: "entity", entity: "sensor.dpc_milano_highest_precipitation", color: "#508BFF" },
    ]);
    assert.equal(map.card.entity, "image.dpc_milano_today_vigilance_map");
    assert.equal(map.rows, 1);
    assert.deepEqual(
      blocks.map(({ card }) => [card.entity, card.color]),
      [["sensor.dpc_milano_today_precipitation", "#C3FFFE"]],
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
