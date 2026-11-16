// Tests of the DPC Alert card: node --test tests/frontend
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  cardLayout,
  cardModel,
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
  "sensor.dpc_milano_tomorrow_precipitation": "none",
  "sensor.dpc_milano_after_tomorrow_precipitation": "heavy",
});

/** Return a Home Assistant with the states of Milano. */
const withStates = (options = {}) => ({ ...homeAssistant(options), states: MILANO });

/** Return the place Milano of the fixtures. */
const milano = (hass = homeAssistant()) => placeOf(findPlaces(hass), { device_id: "milano" });

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
    const model = cardModel(milano(), MILANO);
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
    const days = cardModel(milano(), MILANO).days;
    assert.deepEqual(
      days.map(({ day, name, alert, precipitation }) => [
        day,
        name,
        alert?.color,
        precipitation?.color,
      ]),
      [
        ["today", "Today", "#f0bf01", "#C3FFFE"],
        ["tomorrow", "Tomorrow", "#90c985", "#FFFFFF"],
        // Only the vigilance bulletin covers the day after tomorrow
        ["aftertomorrow", "Day after tomorrow", undefined, "#508BFF"],
      ],
    );
    assert.equal(days[2].alert, undefined);
  });

  it("has no color without data", () => {
    const states = statesOf({ "sensor.dpc_milano_today_alert": "unavailable" });
    const [today] = cardModel(milano(), states).days;
    assert.deepEqual(today.alert, { entity: "sensor.dpc_milano_today_alert", color: undefined });
    assert.deepEqual(today.precipitation, {
      entity: "sensor.dpc_milano_today_precipitation",
      color: undefined,
    });
    assert.equal(swatch(states, undefined, {}), undefined);
  });

  it("is made of native cards: a heading, and a row of tiles for each day", () => {
    const hass = withStates();
    assert.deepEqual(placeLayout(hass, cardModel(milano(hass), hass.states)), {
      heading: {
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
      rows: [
        [
          { type: "tile", entity: "sensor.dpc_milano_today_alert", name: "Today", color: "#f0bf01" },
          {
            type: "tile",
            entity: "sensor.dpc_milano_today_precipitation",
            name: { type: "entity" },
            color: "#C3FFFE",
          },
        ],
        [
          {
            type: "tile",
            entity: "sensor.dpc_milano_tomorrow_alert",
            name: "Tomorrow",
            color: "#90c985",
          },
          {
            type: "tile",
            entity: "sensor.dpc_milano_tomorrow_precipitation",
            name: { type: "entity" },
            color: "#FFFFFF",
          },
        ],
        // Without an alert, the precipitation is named after the day, as wide as the row
        [
          {
            type: "tile",
            entity: "sensor.dpc_milano_after_tomorrow_precipitation",
            name: "Day after tomorrow",
            color: "#508BFF",
          },
        ],
      ],
    });
  });

  it("leaves the color of the theme to states without data", () => {
    const hass = { ...homeAssistant(), states: {} };
    const { heading, rows } = placeLayout(hass, cardModel(milano(hass), hass.states));
    assert.deepEqual(heading.badges, [
      { type: "entity", entity: "sensor.dpc_milano_highest_alert" },
      { type: "entity", entity: "sensor.dpc_milano_highest_precipitation" },
    ]);
    assert.equal(rows[0][0].color, undefined);
  });

  it("names the precipitation with its whole name before Home Assistant 2025.11", () => {
    const hass = withStates({ version: "2025.10.0" });
    const { rows } = placeLayout(hass, cardModel(milano(hass), hass.states));
    assert.equal(rows[0][1].name, undefined);
  });

  it("has no row for a day without its entities", () => {
    const hass = withStates();
    const place = milano(hass);
    place.entries = place.entries.filter(({ day }) => day !== "tomorrow");
    const { rows } = placeLayout(hass, cardModel(place, hass.states));
    assert.deepEqual(
      rows.map((row) => row[0].name),
      ["Today", "Day after tomorrow"],
    );
  });

  it("asks for a place when there is none", () => {
    const hass = withStates({ language: "it" });
    assert.deepEqual(cardLayout(hass, [], {}), {
      heading: undefined,
      rows: [
        [
          {
            type: "markdown",
            content:
              "Aggiungi un luogo dell'integrazione Dipartimento Protezione Civile per vederne qui le allerte.",
          },
        ],
      ],
    });
  });

  it("heads the card with the place of its device", () => {
    const hass = withStates();
    const { heading } = cardLayout(hass, findPlaces(hass), { device_id: "roma" });
    assert.equal(heading.heading, "Roma");
  });
});
