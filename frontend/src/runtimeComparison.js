const RUNTIMES = [
  ["python", "Python"],
  ["node", "Node"],
  ["java", "Java"],
  ["ruby", "Ruby"],
];

function readValue(section, runtime) {
  const entry = section?.[runtime];
  const value =
    entry && typeof entry === "object" && "value" in entry
      ? entry.value
      : entry;

  return value === undefined || value === null || value === ""
    ? null
    : String(value);
}

function formatRuntimeValues(section) {
  return RUNTIMES
    .map(([runtime, label]) => {
      const value = readValue(section, runtime);
      return value ? `${label} ${value}` : null;
    })
    .filter(Boolean)
    .join(" · ");
}

function declaredRuntimes(fingerprint) {
  if (Object.keys(fingerprint?.runtime_declarations || {}).length) {
    return fingerprint.runtime_declarations;
  }

  if (
    fingerprint?.schema_version === "1.0" &&
    ["repository", "ci"].includes(fingerprint?.source?.type)
  ) {
    return fingerprint.runtimes || {};
  }

  return {};
}

function observedRuntimes(fingerprint) {
  return fingerprint?.source?.type === "local"
    ? fingerprint.runtimes || {}
    : {};
}

function comparisonStatus(features, suffix, mismatchValue = 0) {
  const keys = RUNTIMES.map(
    ([runtime]) => `${runtime}_${suffix}`
  );
  const results = keys
    .filter((key) => features?.[key] === 0 || features?.[key] === 1)
    .map((key) => features[key]);

  if (!results.length) {
    return "unknown";
  }

  return results.includes(mismatchValue) ? "mismatch" : "compatible";
}

export function runtimeComparisonStatus(features) {
  const statuses = [
    comparisonStatus(features, "version_match"),
    comparisonStatus(features, "declaration_version_match"),
    comparisonStatus(features, "requirement_violation", 1),
  ];

  if (statuses.includes("mismatch")) {
    return "mismatch";
  }

  return statuses.includes("compatible") ? "compatible" : "unknown";
}

function runtimeUsedForRequirement(fingerprint) {
  const observed = observedRuntimes(fingerprint);
  const declared = declaredRuntimes(fingerprint);
  const values = {};

  for (const [runtime] of RUNTIMES) {
    const observedValue = readValue(observed, runtime);
    const declaredValue = readValue(declared, runtime);
    if (observedValue) {
      values[runtime] = `${observedValue} (observed)`;
    } else if (declaredValue) {
      values[runtime] = `${declaredValue} (declared)`;
    }
  }

  return RUNTIMES
    .map(([runtime, label]) =>
      values[runtime] ? `${label} ${values[runtime]}` : null
    )
    .filter(Boolean)
    .join(" · ");
}

function formatRequirements(section) {
  return RUNTIMES
    .map(([runtime, label]) => {
      const value = readValue(section, runtime);
      return value ? `${label} ${value}` : null;
    })
    .filter(Boolean)
    .join(" · ");
}

export function buildRuntimeComparisonRows(dev, ci, features) {
  return [
    {
      label: "Observed runtime versions",
      dev: formatRuntimeValues(observedRuntimes(dev)) || "Not observed",
      ci: formatRuntimeValues(observedRuntimes(ci)) || "Not observed",
      status: comparisonStatus(features, "version_match"),
    },
    {
      label: "Declared runtime versions",
      dev: formatRuntimeValues(declaredRuntimes(dev)) || "Not declared",
      ci: formatRuntimeValues(declaredRuntimes(ci)) || "Not declared",
      status: comparisonStatus(
        features,
        "declaration_version_match"
      ),
    },
    {
      label: "Runtime requirement check",
      dev: formatRequirements(dev?.requirements) || "No requirement",
      ci: runtimeUsedForRequirement(ci) || "No comparable CI runtime",
      status: comparisonStatus(
        features,
        "requirement_violation",
        1
      ),
    },
  ];
}
