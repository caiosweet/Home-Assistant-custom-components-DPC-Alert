// Tests of the DPC Alert card: node --test tests/frontend
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  cardLayout,
  cardModel,
  dayName,
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
        column: "alert",
      },
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_today_precipitation",
          name: { type: "entity" },
          color: "#C3FFFE",
        },
        column: "precipitation",
      },
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_tomorrow_alert",
          name: "Tomorrow",
          color: "#90c985",
        },
        column: "alert",
      },
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_tomorrow_precipitation",
          name: { type: "entity" },
          color: "#50FFFF",
        },
        column: "precipitation",
      },
      // Without an alert, the precipitation keeps its column, named after the day
      {
        card: {
          type: "tile",
          entity: "sensor.dpc_milano_after_tomorrow_precipitation",
          name: "Day after tomorrow",
          color: "#508BFF",
        },
        column: "precipitation",
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
    assert.deepEqual(cardLayout(hass, [], {}), [
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
    const [heading] = cardLayout(hass, findPlaces(hass), { device_id: "roma" });
    assert.equal(heading.card.heading, "Roma");
  });
});
