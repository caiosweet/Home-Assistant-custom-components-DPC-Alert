// Fixtures of the tests of the frontend: DPC places as Home Assistant has them.

/** The days of a place: how entity IDs and device names say them. */
export const DAYS = {
  today: { id: "today", name: "Today" },
  tomorrow: { id: "tomorrow", name: "Tomorrow" },
  aftertomorrow: { id: "after_tomorrow", name: "Day after tomorrow" },
};

/** Return the devices of a DPC place: the place, and its days linked to it. */
export function placeDevices(id, name) {
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
export function placeEntities(device, prefix, phenomena = []) {
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
export function homeAssistant({ version = "2026.11.0", language = "en", entities = [] } = {}) {
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

