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
  if (
    fingerprint?.schema_version === "1.0" &&
    ["repository", "ci"].includes(fingerprint?.source?.type)
  ) {
    return {
      ...(fingerprint.runtimes || {}),
      ...(fingerprint.runtime_declarations || {}),
    };
  }

  return fingerprint?.runtime_declarations || {};
}

function observedRuntimes(fingerprint) {
  return fingerprint?.source?.type === "local"
    ? fingerprint.runtimes || {}
    : {};
}

export function comparisonStatus(features, suffix, mismatchValue = 0) {
  const keys = RUNTIMES.map(
    ([runtime]) => `${runtime}_${suffix}`
  );
  return featureKeysStatus(features, keys, mismatchValue);
}

function featureKeysStatus(features, keys, mismatchValue) {
  const applicableKeys = keys.filter((key) =>
    Object.prototype.hasOwnProperty.call(features || {}, key)
  );
  if (!applicableKeys.length) {
    return "unknown";
  }

  return aggregateStatus(
    applicableKeys.map((key) =>
      featureStatus(features[key], mismatchValue)
    )
  );
}

export function featureStatus(value, mismatchValue) {
  if (value !== 0 && value !== 1) {
    return "unknown";
  }
  return value === mismatchValue ? "mismatch" : "compatible";
}

export function compatibilityStatuses(features) {
  const runtimeChecks = [
    ...RUNTIMES.map(([runtime]) => [`${runtime}_version_match`, 0]),
    ...RUNTIMES.map(([runtime]) => [
      `${runtime}_declaration_version_match`,
      0,
    ]),
    ...RUNTIMES.slice(0, 3).map(([runtime]) => [
      `${runtime}_requirement_violation`,
      1,
    ]),
  ];
  const runtimeStatus = featureChecksStatus(features, runtimeChecks);
  const osStatus = aggregateStatus([
    featureChecksStatus(
      features,
      [
        ["os_match", 0],
        ["architecture_match", 0],
        ["libc_match", 0],
      ],
      true
    ),
  ]);

  return {
    runtime: runtimeStatus,
    dependencies: featureStatus(
      features?.dependency_environment_conflict,
      1
    ),
    os: osStatus,
    configuration: featureStatus(
      features?.required_env_missing,
      1
    ),
    resources: featureStatus(
      features?.resource_constraint_detected,
      1
    ),
  };
}

export function runtimeComparisonStatus(features) {
  return compatibilityStatuses(features).runtime;
}

function featureChecksStatus(features, checks, requireAll = false) {
  const applicable = checks
    .filter(
      ([key]) =>
        requireAll ||
        Object.prototype.hasOwnProperty.call(features || {}, key)
    )
    .map(([key, mismatchValue]) =>
      featureStatus(features[key], mismatchValue)
    );

  return aggregateStatus(applicable);
}

function aggregateStatus(statuses) {
  if (statuses.includes("mismatch")) {
    return "mismatch";
  }
  if (!statuses.length || statuses.includes("unknown")) {
    return "unknown";
  }
  return "compatible";
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
      status: Object.keys(dev?.requirements || {}).some((runtime) =>
        ["node", "python", "java"].includes(runtime)
      )
        ? comparisonStatus(features, "requirement_violation", 1)
        : "not_applicable",
    },
  ];
}
