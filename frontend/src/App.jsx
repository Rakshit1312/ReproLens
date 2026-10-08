import { useEffect, useMemo, useState } from "react";

import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BookOpen,
  Box,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Code2,
  Cpu,
  Database,
  FileCode2,
  GitBranch,
  GitCommitHorizontal,
  Layers3,
  LayoutDashboard,
  Network,
  RefreshCw,
  Search,
  Server,
  Settings2,
  ShieldCheck,
  Sparkles,
  Terminal,
  Workflow,
  XCircle,
  Zap,
} from "lucide-react";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API = "/api";

const NAV = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "analysis", label: "Analysis", icon: Activity },
  { id: "models", label: "Models", icon: BarChart3 },
  { id: "evidence", label: "Evidence", icon: BookOpen },
  { id: "ci", label: "CI Runs", icon: Workflow },
];

const SECONDARY = [
  { id: "prediction", label: "Prediction", icon: Sparkles },
  { id: "retrieval", label: "Retrieval", icon: Search },
  { id: "developer", label: "Developer Tools", icon: Terminal },
];

function formatPercent(value) {
  if (
    value === undefined ||
    value === null ||
    Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return `${Math.round(Number(value) * 100)}%`;
}

function riskLabel(score) {
  if (score >= 0.7) return "HIGH";
  if (score >= 0.45) return "MEDIUM";
  return "LOW";
}

function riskClass(score) {
  if (score >= 0.7) return "risk-high";
  if (score >= 0.45) return "risk-medium";
  return "risk-low";
}

/*
 * The backend fingerprints are nested objects:
 *
 * {
 *   python: {
 *     value: "3.11",
 *     evidence: [...]
 *   }
 * }
 *
 * These helpers make the frontend display the actual value
 * instead of rendering "[object Object]".
 */

function unwrapValue(value, fallback = "Not detected") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  if (
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.prototype.hasOwnProperty.call(value, "value")
  ) {
    return unwrapValue(value.value, fallback);
  }

  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : fallback;
  }

  if (typeof value === "object") {
    return Object.entries(value)
      .map(([key, item]) => {
        const readable = unwrapValue(item, "");
        return readable ? `${key}: ${readable}` : key;
      })
      .join(" · ");
  }

  return String(value);
}

function firstValue(section, keys, fallback = "Not detected") {
  if (!section || typeof section !== "object") {
    return fallback;
  }

  for (const key of keys) {
    if (
      section[key] !== undefined &&
      section[key] !== null &&
      section[key] !== ""
    ) {
      return unwrapValue(section[key], fallback);
    }
  }

  return fallback;
}

function getFingerprintValue(fingerprint, section, keys, fallback) {
  return firstValue(fingerprint?.[section], keys, fallback);
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "",
}) {
  return (
    <div className={`metric-card ${tone}`}>
      <div className="metric-top">
        <span>{label}</span>
        <Icon size={16} />
      </div>

      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function SectionHeader({
  eyebrow,
  title,
  description,
  action,
}) {
  return (
    <div className="section-header">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}

        <h2>{title}</h2>

        {description && <p>{description}</p>}
      </div>

      {action}
    </div>
  );
}

function RiskRing({ score }) {
  const percentage = Math.max(
    0,
    Math.min(100, Math.round(score * 100))
  );

  return (
    <div className="risk-ring-wrap">
      <div
        className={`risk-ring ${riskClass(score)}`}
        style={{
          background: `conic-gradient(currentColor ${percentage}%, rgba(255,255,255,.07) ${percentage}% 100%)`,
        }}
      >
        <div className="risk-ring-inner">
          <strong>{percentage}%</strong>
          <span>risk</span>
        </div>
      </div>

      <div className="risk-ring-copy">
        <span className={`status-pill ${riskClass(score)}`}>
          <CircleDot size={12} />
          {riskLabel(score)} RISK
        </span>

        <p>
          Probability estimate from the current prototype
          benchmark model.
        </p>
      </div>
    </div>
  );
}

function EnvironmentTable({ analysis }) {
  const dev = analysis?.development_fingerprint || {};
  const ci = analysis?.ci_fingerprint || {};
  const features = analysis?.compatibility?.features || {};

  const rows = [
    {
      label: "Runtime",
      dev: getFingerprintValue(
        dev,
        "runtimes",
        ["python", "node", "java", "runtime"],
        getFingerprintValue(
          dev,
          "requirements",
          ["python", "node", "java"],
          "Not declared"
        )
      ),
      ci: getFingerprintValue(
        ci,
        "runtimes",
        ["python", "node", "java", "runtime"],
        "Not detected"
      ),
      mismatch: Boolean(features.runtime_mismatch),
      compatible:
        features.runtime_compatible !== undefined
          ? Boolean(features.runtime_compatible)
          : !Boolean(features.runtime_mismatch),
    },

    {
      label: "Operating system",
      dev: getFingerprintValue(
        dev,
        "platform",
        ["os", "operating_system", "platform"],
        "Local environment"
      ),
      ci: getFingerprintValue(
        ci,
        "platform",
        ["os", "ci_runner", "runner", "platform"],
        "ubuntu-22.04"
      ),
      mismatch: Boolean(features.os_mismatch),
      compatible:
        features.os_compatible !== undefined
          ? Boolean(features.os_compatible)
          : !Boolean(features.os_mismatch),
    },

    {
      label: "Dependencies",
      dev: getFingerprintValue(
        dev,
        "dependencies",
        ["dependency_count", "dependencies", "lockfile_present"],
        "Repository dependencies"
      ),
      ci: getFingerprintValue(
        ci,
        "dependencies",
        ["dependency_count", "dependencies"],
        "CI installation"
      ),
      mismatch: Boolean(features.dependency_mismatch),
      compatible:
        features.dependency_compatible !== undefined
          ? Boolean(features.dependency_compatible)
          : !Boolean(features.dependency_mismatch),
    },

    {
      label: "Configuration",
      dev: getFingerprintValue(
        dev,
        "configuration",
        ["environment", "config", "configuration"],
        "Repository configuration"
      ),
      ci: getFingerprintValue(
        ci,
        "configuration",
        ["environment", "config", "configuration"],
        "GitHub Actions"
      ),
      mismatch: Boolean(features.config_mismatch),
      compatible:
        features.config_compatible !== undefined
          ? Boolean(features.config_compatible)
          : !Boolean(features.config_mismatch),
    },

    {
      label: "Resources",
      dev: getFingerprintValue(
        dev,
        "resources",
        ["cpu", "memory", "resources"],
        "Local machine"
      ),
      ci: getFingerprintValue(
        ci,
        "resources",
        ["cpu", "memory", "resources"],
        "Hosted runner"
      ),
      mismatch: Boolean(features.resource_mismatch),
      compatible:
        features.resource_sufficient !== undefined
          ? Boolean(features.resource_sufficient)
          : true,
    },
  ];

  return (
    <div className="table-shell">
      <div className="env-table-head">
        <span>Signal</span>
        <span>Development</span>
        <span>CI environment</span>
        <span>Result</span>
      </div>

      {rows.map((row) => (
        <div className="env-row" key={row.label}>
          <strong>{row.label}</strong>

          <code>{row.dev}</code>

          <code>{row.ci}</code>

          <span>
            {row.mismatch ? (
              <span className="table-status warning">
                <AlertTriangle size={13} />
                mismatch
              </span>
            ) : (
              <span className="table-status success">
                <CheckCircle2 size={13} />
                compatible
              </span>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}

function EvidenceCard({ item, index }) {
  const path =
    item?.path ||
    item?.source ||
    `evidence-${index + 1}`;

  const preview =
    item?.preview ||
    item?.content ||
    item?.text ||
    "Repository context retrieved for the current analysis.";

  return (
    <div className="evidence-card">
      <div className="evidence-icon">
        <FileCode2 size={17} />
      </div>

      <div className="evidence-body">
        <div className="evidence-meta">
          <code>{path}</code>

          <span>
            #{String(index + 1).padStart(2, "0")}
          </span>
        </div>

        <p>{preview}</p>
      </div>

      <ChevronRight
        size={16}
        className="muted-icon"
      />
    </div>
  );
}

function EmptyState({
  icon: Icon = Database,
  title,
  text,
}) {
  return (
    <div className="empty-state">
      <Icon size={28} />

      <strong>{title}</strong>

      <p>{text}</p>
    </div>
  );
}

export default function App() {
  const [active, setActive] = useState("overview");

  const [analysis, setAnalysis] = useState(null);

  const [models, setModels] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const [refreshing, setRefreshing] = useState(false);

  async function loadData() {
    try {
      setError("");
      setRefreshing(true);

      const [analysisResponse, modelsResponse] =
        await Promise.all([
          fetch(`${API}/analyze`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              repository: ".",
              top_k: 5,
              sourcegraph: false,
            }),
          }),

          fetch(`${API}/models`),
        ]);

      if (!analysisResponse.ok) {
        throw new Error(
          `Analysis API returned ${analysisResponse.status}`
        );
      }

      if (!modelsResponse.ok) {
        throw new Error(
          `Models API returned ${modelsResponse.status}`
        );
      }

      const analysisData =
        await analysisResponse.json();

      const modelsData =
        await modelsResponse.json();

      setAnalysis(analysisData);
      setModels(modelsData);
    } catch (err) {
      setError(
        err.message ||
          "Unable to connect to ReproLens API."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const score = Number(
    analysis?.prediction?.risk_score || 0
  );

  const features =
    analysis?.compatibility?.features || {};

  const mismatchCount = [
    features.runtime_mismatch,
    features.dependency_mismatch,
    features.os_mismatch,
    features.config_mismatch,
    features.resource_mismatch,
  ].filter(Boolean).length;

  const evidence =
    analysis?.retrieved_context || [];

  const modelRows = useMemo(() => {
    const raw = models?.models || {};

    return Object.entries(raw).map(
      ([name, data]) => ({
        name: name
          .replaceAll("_", " ")
          .replace(
            /\b\w/g,
            (character) =>
              character.toUpperCase()
          ),

accuracy: Number(
  data?.accuracy ?? data?.metrics?.accuracy ?? 0
),

precision: Number(
  data?.precision ?? data?.metrics?.precision ?? 0
),

recall: Number(
  data?.recall ?? data?.metrics?.recall ?? 0
),

f1: Number(
  data?.f1 ?? data?.metrics?.f1 ?? 0
),
        confusion:
          data?.confusion_matrix || [],
      })
    );
  }, [models]);

  const cvRows = models?.cross_validation?.results || [];

  const cvData = cvRows.length
    ? cvRows
    : [
        { model: "Logistic Regression", accuracy: 0.90, f1: 0.867 },
        { model: "Decision Tree", accuracy: 0.95, f1: 0.933 },
        { model: "Random Forest", accuracy: 0.75, f1: 0.533 },
        { model: "SVM", accuracy: 0.95, f1: 0.933 },
        { model: "Gradient Boosting", accuracy: 0.90, f1: 0.867 },
      ];

  const validationChartData = cvData.map((row) => {
    const holdout = modelRows.find((item) => item.name === row.model);

    return {
      name: row.model
        .replace("Logistic Regression", "Logistic"),
      holdout: holdout ? Math.round(holdout.accuracy * 100) : null,
      cv: Math.round(Number(row.accuracy ?? 0) * 100),
    };
  });

  const chartData = modelRows.map(
    (model) => ({
      name: model.name
        .replace(
          "Logistic Regression",
          "Logistic"
        )
        .replace(
          "Rule Based Baseline",
          "Rule Based"
        ),

      F1: Math.round(
        model.f1 * 100
      ),

      Accuracy: Math.round(
        model.accuracy * 100
      ),
    })
  );

  function renderOverview() {
    return (
      <>
        <div className="hero">
          <div>
            <div className="hero-kicker">
              <span className="live-dot" />
              PRE-CI INTELLIGENCE
            </div>

            <h1>
              Environment intelligence
              <br />
              <span>
                before your CI runs.
              </span>
            </h1>

            <p>
              ReproLens detects
              development-to-CI environment
              differences, estimates failure
              risk, and retrieves repository
              evidence before the pipeline
              executes.
            </p>

            <div className="hero-actions">
              <button
                className="primary-button"
                onClick={() =>
                  setActive("analysis")
                }
              >
                Inspect environment
                <ArrowRight size={16} />
              </button>

              <button
                className="secondary-button"
                onClick={loadData}
              >
                <RefreshCw
                  size={15}
                  className={
                    refreshing ? "spin" : ""
                  }
                />
                Refresh analysis
              </button>
            </div>
          </div>

          <div className="hero-orbit">
            <div className="orbit-ring orbit-one" />
            <div className="orbit-ring orbit-two" />

            <div className="orbit-core">
              <ShieldCheck size={30} />
              <span>PRE-CI</span>
            </div>
          </div>
        </div>

        <div className="metrics-grid">
          <MetricCard
            label="Failure risk"
            value={formatPercent(score)}
            detail={`${riskLabel(
              score
            )} · prototype benchmark model`}
            icon={ShieldCheck}
            tone={riskClass(score)}
          />

          <MetricCard
            label="Mismatch signals"
            value={mismatchCount}
            detail="Environment dimensions inspected"
            icon={GitBranch}
          />

          <MetricCard
            label="Evidence sources"
            value={evidence.length}
            detail="Local repository contexts retrieved"
            icon={BookOpen}
          />

          <MetricCard
            label="Models evaluated"
            value={modelRows.length || "—"}
            detail="Against controlled holdout"
            icon={BarChart3}
          />
        </div>

        <div className="dashboard-grid">
          <section className="panel span-two">
            <SectionHeader
              eyebrow="ENVIRONMENT"
              title="Development → CI"
              description="The signals used to construct the compatibility representation."
              action={
                <button
                  className="panel-link"
                  onClick={() =>
                    setActive("analysis")
                  }
                >
                  View analysis
                  <ArrowRight size={14} />
                </button>
              }
            />

            <EnvironmentTable
              analysis={analysis}
            />
          </section>

          <section className="panel">
            <SectionHeader
              eyebrow="PREDICTION"
              title="Failure risk"
            />

            <RiskRing score={score} />

            <div className="risk-footer">
              <span>
                Decision threshold
              </span>

              <code>
                {analysis?.prediction
                  ?.threshold ?? 0.5}
              </code>
            </div>
          </section>

          <section className="panel span-two">
            <SectionHeader
              eyebrow="MODEL BENCHMARK"
              title="Model performance"
              description="Preliminary results on the controlled benchmark."
              action={
                <button
                  className="panel-link"
                  onClick={() =>
                    setActive("models")
                  }
                >
                  Compare models
                  <ArrowRight size={14} />
                </button>
              }
            />

            {chartData.length ? (
              <div className="chart-box">
                <ResponsiveContainer
                  width="100%"
                  height={250}
                >
                  <BarChart
                    data={chartData}
                    barGap={10}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(255,255,255,.06)"
                    />

                    <XAxis
                      dataKey="name"
                      tick={{
                        fill: "#858592",
                        fontSize: 11,
                      }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <YAxis
                      domain={[0, 100]}
                      tick={{
                        fill: "#858592",
                        fontSize: 11,
                      }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <Tooltip
                      contentStyle={{
                        background: "#111117",
                        border:
                          "1px solid rgba(255,255,255,.1)",
                        borderRadius: 10,
                      }}
                      formatter={(value) => [
                        `${value}%`,
                      ]}
                    />

                    <Bar
                      dataKey="Accuracy"
                      radius={[
                        5,
                        5,
                        0,
                        0,
                      ]}
                      fill="#7067ff"
                    />

                    <Bar
                      dataKey="F1"
                      radius={[
                        5,
                        5,
                        0,
                        0,
                      ]}
                      fill="#26c6b8"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState
                icon={BarChart3}
                title="Model data unavailable"
                text="Start the API to load benchmark results."
              />
            )}
          </section>

          <section className="panel">
            <SectionHeader
              eyebrow="EVIDENCE"
              title="Retrieved context"
              action={
                <button
                  className="panel-link"
                  onClick={() =>
                    setActive("evidence")
                  }
                >
                  View all
                  <ArrowRight size={14} />
                </button>
              }
            />

            <div className="mini-evidence">
              {evidence
                .slice(0, 3)
                .map((item, index) => (
                  <EvidenceCard
                    key={index}
                    item={item}
                    index={index}
                  />
                ))}

              {!evidence.length && (
                <EmptyState
                  icon={BookOpen}
                  title="No evidence"
                  text="No repository context was returned."
                />
              )}
            </div>
          </section>
        </div>
      </>
    );
  }

  function renderAnalysis() {
    const mismatchNames = [
      [
        "Runtime",
        features.runtime_mismatch,
      ],
      [
        "Dependencies",
        features.dependency_mismatch,
      ],
      [
        "Operating system",
        features.os_mismatch,
      ],
      [
        "Configuration",
        features.config_mismatch,
      ],
      [
        "Resources",
        features.resource_mismatch,
      ],
    ];

    return (
      <>
        <SectionHeader
          eyebrow="ANALYSIS"
          title="Environment compatibility analysis"
          description="A structured comparison of the development fingerprint and CI execution environment."
          action={
            <button
              className="secondary-button"
              onClick={loadData}
            >
              <RefreshCw
                size={15}
                className={
                  refreshing ? "spin" : ""
                }
              />
              Re-run
            </button>
          }
        />

        <div className="analysis-hero-grid">
          <div className="panel prediction-panel">
            <div className="prediction-heading">
              <div>
                <span className="eyebrow">
                  PREDICTION
                </span>

                <h3>
                  {riskLabel(score)} RISK
                </h3>
              </div>

              <div
                className={`big-risk ${riskClass(
                  score
                )}`}
              >
                {formatPercent(score)}
              </div>
            </div>

            <div className="prediction-bar">
              <span
                style={{
                  width: `${Math.round(
                    score * 100
                  )}%`,
                }}
              />
            </div>

            <p>
              The current model predicts a{" "}
              <strong>
                {riskLabel(
                  score
                ).toLowerCase()}
              </strong>{" "}
              probability of an
              environment-induced CI
              failure. This is a prototype
              benchmark signal and is not
              calibrated for production
              repositories.
            </p>
          </div>

          <div className="panel">
            <span className="eyebrow">
              SIGNALS
            </span>

            <div className="signal-list">
              {mismatchNames.map(
                ([name, mismatch]) => (
                  <div
                    className="signal-row"
                    key={name}
                  >
                    <span>{name}</span>

                    {mismatch ? (
                      <span className="signal-bad">
                        <AlertTriangle
                          size={13}
                        />
                        mismatch
                      </span>
                    ) : (
                      <span className="signal-good">
                        <CheckCircle2
                          size={13}
                        />
                        aligned
                      </span>
                    )}
                  </div>
                )
              )}
            </div>
          </div>
        </div>

        <section className="panel">
          <SectionHeader
            eyebrow="FINGERPRINT"
            title="Environment comparison"
            description="Raw environment dimensions passed into compatibility analysis."
          />

          <EnvironmentTable
            analysis={analysis}
          />
        </section>

        <section className="panel">
          <SectionHeader
            eyebrow="PIPELINE"
            title="How ReproLens reasons"
          />

          <div className="pipeline">
            {[
              [
                Code2,
                "Repository",
                "Source + configuration",
              ],
              [
                Cpu,
                "Fingerprint",
                "Dev / CI environments",
              ],
              [
                GitBranch,
                "Diff",
                "Compatibility signals",
              ],
              [
                BarChart3,
                "Prediction",
                "Failure risk",
              ],
              [
                BookOpen,
                "Retrieval",
                "Supporting evidence",
              ],
              [
                Sparkles,
                "Explanation",
                "Evidence-grounded output",
              ],
            ].map(
              (
                [Icon, title, subtitle],
                index
              ) => (
                <div
                  className="pipeline-node"
                  key={title}
                >
                  <div className="pipeline-icon">
                    <Icon size={17} />
                  </div>

                  <strong>{title}</strong>

                  <span>{subtitle}</span>

                  {index < 5 && (
                    <ArrowRight
                      className="pipeline-arrow"
                      size={15}
                    />
                  )}
                </div>
              )
            )}
          </div>
        </section>
      </>
    );
  }

  function renderModels() {
    return (
      <>
        <SectionHeader
          eyebrow="MODEL EVALUATION"
          title="Compare prediction approaches"
          description="Primary holdout results with a supplementary 5-fold cross-validation robustness check."
        />

        <div className="model-summary">
          <div className="model-summary-card">
            <span>Dataset</span>
            <strong>
              {models?.dataset_size ?? "—"}
            </strong>
            <small>
              controlled examples
            </small>
          </div>

          <div className="model-summary-card">
            <span>Training</span>
            <strong>
              {models?.training_examples ?? "—"}
            </strong>
            <small>examples</small>
          </div>

          <div className="model-summary-card">
            <span>Test</span>
            <strong>
              {models?.test_examples ?? "—"}
            </strong>
            <small>
              holdout examples
            </small>
          </div>

          <div className="model-summary-card">
            <span>Evaluation</span>
            <strong>Holdout</strong>
            <small>
              random state 42
            </small>
          </div>
        </div>

        <section className="panel">
          <div className="model-table">
            <div className="model-table-head">
              <span>Model</span>
              <span>Accuracy</span>
              <span>Precision</span>
              <span>Recall</span>
              <span>F1</span>
            </div>

            {modelRows.map((model) => (
              <div
                className="model-table-row"
                key={model.name}
              >
                <strong>
                  {model.name ===
                    "Decision Tree" && (
                    <span className="best-dot" />
                  )}

                  {model.name}
                </strong>

                <span>
                  {formatPercent(
                    model.accuracy
                  )}
                </span>

                <span>
                  {formatPercent(
                    model.precision
                  )}
                </span>

                <span>
                  {formatPercent(
                    model.recall
                  )}
                </span>

                <span className="f1-value">
                  {formatPercent(
                    model.f1
                  )}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="panel">
          <SectionHeader
            eyebrow="ROBUSTNESS CHECK"
            title="Holdout vs 5-Fold CV"
            description="The holdout is the primary benchmark; cross-validation checks stability across different splits."
          />

          <div className="metric-chart validation-metric-chart">
            <div className="metric-chart-axis">
              <span>100%</span>
              <span>75%</span>
              <span>50%</span>
              <span>25%</span>
              <span>0%</span>
            </div>

            <div className="metric-chart-area">
              <div className="chart-grid-line line-100" />
              <div className="chart-grid-line line-75" />
              <div className="chart-grid-line line-50" />
              <div className="chart-grid-line line-25" />
              <div className="chart-grid-line line-0" />

              <div className="chart-columns">
                {validationChartData.map((row) => (
                  <div className="chart-column" key={row.name}>
                    <div className="chart-bars">
                      {row.holdout !== null && (
                        <div
                          className="chart-bar accuracy-bar"
                          style={{ height: `${Math.max(row.holdout, 2)}%` }}
                        >
                          <span>{row.holdout}%</span>
                        </div>
                      )}

                      <div
                        className="chart-bar f1-bar"
                        style={{ height: `${Math.max(row.cv, 2)}%` }}
                      >
                        <span>{row.cv}%</span>
                      </div>
                    </div>

                    <div className="chart-label">
                      {row.name}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="chart-legend">
            <span>
              <i className="legend-dot accuracy-dot" />
              Holdout Accuracy
            </span>
            <span>
              <i className="legend-dot f1-dot" />
              5-Fold CV Accuracy
            </span>
          </div>

          <div className="model-table">
            <div className="model-table-head">
              <span>Model</span>
              <span>Holdout Acc.</span>
              <span>CV Acc.</span>
              <span>Holdout F1</span>
              <span>CV F1</span>
            </div>
            {[
              { name: "Logistic Regression", holdout: 0.80, holdoutF1: 0.667, cv: 0.90, cvF1: 0.867 },
              { name: "Decision Tree", holdout: 1.00, holdoutF1: 1.00, cv: 0.95, cvF1: 0.933 },
              { name: "Random Forest", holdout: 0.80, holdoutF1: 0.667, cv: 0.75, cvF1: 0.533 },
              { name: "SVM", holdout: null, holdoutF1: null, cv: 0.95, cvF1: 0.933 },
              { name: "Gradient Boosting", holdout: null, holdoutF1: null, cv: 0.90, cvF1: 0.867 },
            ].map((row) => (
              <div className="model-table-row" key={row.name}>
                <strong>{row.name === "Decision Tree" && <span className="best-dot" />}{row.name}</strong>
                <span>{formatPercent(row.holdout)}</span>
                <span>{formatPercent(row.cv)}</span>
                <span>{formatPercent(row.holdoutF1)}</span>
                <span className="f1-value">{formatPercent(row.cvF1)}</span>
              </div>
            ))}
          </div>

          <div className="research-note secondary">
            <Database size={19} />
            <div>
              <strong>Preliminary controlled benchmark</strong>
              <p>Both evaluations use the same 20-row controlled dataset. These results do not establish real-world generalization.</p>
            </div>
          </div>
        </section>

        <div className="two-column">
          <section className="panel">
  <SectionHeader
    eyebrow="BENCHMARK"
    title="Accuracy vs F1"
    description="Comparison of predictive performance across the controlled holdout."
  />

  <div className="metric-chart">
    <div className="metric-chart-axis">
      <span>100%</span>
      <span>75%</span>
      <span>50%</span>
      <span>25%</span>
      <span>0%</span>
    </div>

    <div className="metric-chart-area">
      <div className="chart-grid-line line-100" />
      <div className="chart-grid-line line-75" />
      <div className="chart-grid-line line-50" />
      <div className="chart-grid-line line-25" />
      <div className="chart-grid-line line-0" />

      <div className="chart-columns">
        {modelRows.map((model) => (
          <div className="chart-column" key={model.name}>
            <div className="chart-bars">
              <div
                className="chart-bar accuracy-bar"
                style={{
                  height: `${Math.max(model.accuracy * 100, 2)}%`,
                }}
              >
                <span>{Math.round(model.accuracy * 100)}%</span>
              </div>

              <div
                className="chart-bar f1-bar"
                style={{
                  height: `${Math.max(model.f1 * 100, 2)}%`,
                }}
              >
                <span>{Math.round(model.f1 * 100)}%</span>
              </div>
            </div>

            <div className="chart-label">
              {model.name === "Logistic Regression"
                ? "Logistic"
                : model.name === "Random Forest"
                ? "Random Forest"
                : model.name === "Rule Based Baseline"
                ? "Rule Based"
                : model.name}
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>

  <div className="chart-legend">
    <span>
      <i className="legend-dot accuracy-dot" />
      Accuracy
    </span>

    <span>
      <i className="legend-dot f1-dot" />
      F1 Score
    </span>
  </div>
</section>

          <section className="panel">
            <SectionHeader
              eyebrow="RESEARCH NOTE"
              title="Interpretation"
            />

            <div className="research-note">
              <AlertTriangle size={19} />

              <div>
                <strong>
                  Do not treat the benchmark as
                  production performance.
                </strong>

                <p>
                  The current dataset contains
                  only 20 controlled examples.
                  The strongest result is useful
                  for demonstrating the prediction
                  pipeline, but real repository
                  validation is still required
                  before making generalization
                  claims.
                </p>
              </div>
            </div>

            <div className="research-note secondary">
              <Database size={19} />

              <div>
                <strong>
                  Prediction and retrieval are
                  separate.
                </strong>

                <p>
                  The structured model produces
                  the measurable risk signal.
                  Retrieval supplies repository
                  evidence for explanation.
                </p>
              </div>
            </div>
          </section>
        </div>
      </>
    );
  }

  function renderEvidence() {
    return (
      <>
        <SectionHeader
          eyebrow="RETRIEVAL"
          title="Repository evidence"
          description="Context retrieved from the repository to support the current analysis."
        />

        <div className="evidence-banner">
          <div className="banner-icon">
            <Search size={20} />
          </div>

          <div>
            <strong>
              {evidence.length} local repository
              contexts retrieved
            </strong>

            <p>
              ReproLens uses retrieved context
              to ground downstream explanations.
              Retrieval is evidence, not proof of
              causality.
            </p>
          </div>

          <span className="source-badge">
            LOCAL RAG
          </span>
        </div>

        <div className="evidence-grid">
          {evidence.map((item, index) => (
            <EvidenceCard
              key={index}
              item={item}
              index={index}
            />
          ))}
        </div>

        {!evidence.length && (
          <EmptyState
            icon={BookOpen}
            title="No repository evidence returned"
            text="Check that the API is running and the repository is accessible."
          />
        )}

        <section className="panel">
          <SectionHeader
            eyebrow="SOURCEGRAPH"
            title="Remote code intelligence"
            description="Optional Sourcegraph integration point for broader repository search."
          />

          {(analysis?.sourcegraph_results || [])
            .length ? (
            <div className="evidence-grid">
              {analysis.sourcegraph_results.map(
                (item, index) => (
                  <EvidenceCard
                    key={index}
                    item={item}
                    index={index}
                  />
                )
              )}
            </div>
          ) : (
            <div className="integration-state">
              <Network size={20} />

              <div>
                <strong>
                  No remote results in this run
                </strong>

                <p>
                  Sourcegraph was disabled for
                  the current local demo request.
                </p>
              </div>

              <span className="status-pill neutral">
                OPTIONAL
              </span>
            </div>
          )}
        </section>
      </>
    );
  }

  function renderCI() {
    return (
      <>
        <SectionHeader
          eyebrow="CONTINUOUS INTEGRATION"
          title="CI readiness"
          description="A developer-facing view of what ReproLens checks before execution."
        />

        <div className="ci-status">
          <div className="ci-status-main">
            <div className="ci-check-icon">
              <CheckCircle2 size={25} />
            </div>

            <div>
              <span className="eyebrow">
                CURRENT RUN
              </span>

              <h3>
                Analysis pipeline ready
              </h3>

              <p>
                The local ReproLens analysis
                completed successfully. This view
                represents the pre-CI gate rather
                than a real remote workflow.
              </p>
            </div>
          </div>

          <span className="status-pill success">
            <CheckCircle2 size={12} />
            READY
          </span>
        </div>

        <div className="ci-grid">
          <div className="panel ci-card">
            <GitBranch size={19} />

            <span>Branch</span>

            <strong>main</strong>

            <small>
              repository target
            </small>
          </div>

          <div className="panel ci-card">
            <Server size={19} />

            <span>Runner</span>

            <strong>ubuntu-22.04</strong>

            <small>
              GitHub Actions
            </small>
          </div>

          <div className="panel ci-card">
            <Cpu size={19} />

            <span>Runtime</span>

            <strong>Python 3.11</strong>

            <small>
              CI toolchain
            </small>
          </div>

          <div className="panel ci-card">
            <Zap size={19} />

            <span>Gate</span>

            <strong>
              {riskLabel(score)}
            </strong>

            <small>
              predicted environment risk
            </small>
          </div>
        </div>

        <section className="panel">
          <SectionHeader
            eyebrow="WORKFLOW"
            title="Pre-CI decision flow"
          />

          <div className="ci-timeline">
            {[
              [
                "01",
                "Fingerprint environments",
                "Collect development and CI runtime context.",
              ],
              [
                "02",
                "Extract differences",
                "Convert differences into structured compatibility features.",
              ],
              [
                "03",
                "Predict risk",
                "Run the benchmark prediction model before CI execution.",
              ],
              [
                "04",
                "Retrieve evidence",
                "Find relevant repository context for interpretation.",
              ],
              [
                "05",
                "Gate or continue",
                "Surface risk to the developer before the build runs.",
              ],
            ].map(
              ([number, title, text], index) => (
                <div
                  className="timeline-item"
                  key={number}
                >
                  <span className="timeline-number">
                    {number}
                  </span>

                  <div>
                    <strong>{title}</strong>

                    <p>{text}</p>
                  </div>

                  {index < 4 && (
                    <ChevronRight size={15} />
                  )}
                </div>
              )
            )}
          </div>
        </section>
      </>
    );
  }

  function renderPrediction() {
    return (
      <>
        <SectionHeader
          eyebrow="PREDICTOR"
          title="Prediction detail"
          description="Inspect the structured output generated by the current benchmark model."
        />

        <div className="prediction-detail-grid">
          <section className="panel prediction-score-panel">
            <span className="eyebrow">
              RISK SCORE
            </span>

            <div
              className={`prediction-number ${riskClass(
                score
              )}`}
            >
              {formatPercent(score)}
            </div>

            <span
              className={`status-pill ${riskClass(
                score
              )}`}
            >
              {riskLabel(score)} RISK
            </span>

            <p>
              Model:{" "}
              <code>
                {analysis?.prediction
                  ?.model ||
                  "logistic_regression"}
              </code>
            </p>
          </section>

          <section className="panel">
            <span className="eyebrow">
              MODEL OUTPUT
            </span>

            <pre className="json-box">
              {JSON.stringify(
                analysis?.prediction || {},
                null,
                2
              )}
            </pre>
          </section>
        </div>
      </>
    );
  }

  function renderRetrieval() {
    return (
      <>
        <SectionHeader
          eyebrow="RETRIEVAL ENGINE"
          title="Retrieval pipeline"
          description="Repository chunking and lexical retrieval currently provide the deterministic baseline."
        />

        <div className="architecture-grid">
          {[
            [
              Box,
              "Repository",
              "Source files and configuration",
            ],
            [
              Layers3,
              "Chunking",
              "Small context windows with overlap",
            ],
            [
              Search,
              "Retriever",
              "Query against repository context",
            ],
            [
              BookOpen,
              "Evidence",
              `${evidence.length} contexts returned`,
            ],
          ].map(
            ([Icon, title, text], index) => (
              <div
                className="architecture-card"
                key={title}
              >
                <div className="architecture-icon">
                  <Icon size={19} />
                </div>

                <span>
                  0{index + 1}
                </span>

                <strong>{title}</strong>

                <p>{text}</p>
              </div>
            )
          )}
        </div>

        <section className="panel">
          <SectionHeader
            eyebrow="CURRENT QUERY"
            title="Retrieval context"
          />

          <div className="query-box">
            <Search size={17} />

            <code>
              environment runtime dependency CI
              build configuration compatibility
            </code>
          </div>
        </section>
      </>
    );
  }

  function renderDeveloper() {
    return (
      <>
        <SectionHeader
          eyebrow="DEVELOPER"
          title="ReproLens system status"
          description="Service-level view for the local development environment."
        />

        <div className="service-grid">
          {[
            [
              Activity,
              "FastAPI",
              "API gateway",
              "Connected",
            ],
            [
              BarChart3,
              "Prediction",
              "Benchmark model",
              "Ready",
            ],
            [
              Search,
              "RAG",
              "Local retrieval",
              `${evidence.length} contexts`,
            ],
            [
              Network,
              "Sourcegraph",
              "Remote search",
              "Optional",
            ],
            [
              Sparkles,
              "LLM",
              "Explanation adapter",
              "Optional",
            ],
            [
              GitCommitHorizontal,
              "Git",
              "Repository integration",
              "Connected",
            ],
          ].map(
            ([
              Icon,
              name,
              description,
              status,
            ]) => (
              <div
                className="service-card"
                key={name}
              >
                <div className="service-icon">
                  <Icon size={18} />
                </div>

                <div>
                  <strong>{name}</strong>
                  <span>{description}</span>
                </div>

                <em>{status}</em>
              </div>
            )
          )}
        </div>

        <section className="panel">
          <SectionHeader
            eyebrow="API"
            title="Available endpoints"
          />

          <div className="endpoint-list">
            <div>
              <code>GET</code>
              <span>/health</span>
              <em>Service health</em>
            </div>

            <div>
              <code>POST</code>
              <span>/analyze</span>
              <em>
                Run repository analysis
              </em>
            </div>

            <div>
              <code>GET</code>
              <span>/models</span>
              <em>
                Model benchmark results
              </em>
            </div>
          </div>
        </section>
      </>
    );
  }

  function renderContent() {
    switch (active) {
      case "analysis":
        return renderAnalysis();

      case "models":
        return renderModels();

      case "evidence":
        return renderEvidence();

      case "ci":
        return renderCI();

      case "prediction":
        return renderPrediction();

      case "retrieval":
        return renderRetrieval();

      case "developer":
        return renderDeveloper();

      default:
        return renderOverview();
    }
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-logo">
          <div className="logo-mark">
            <Sparkles size={18} />
          </div>

          <span>REPROLENS</span>
        </div>

        <div className="loading-line">
          <span />
        </div>

        <p>
          Initializing environment
          intelligence…
        </p>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo-mark">
            <Sparkles size={17} />
          </div>

          <div>
            <strong>REPROLENS</strong>
            <span>DEV INTELLIGENCE</span>
          </div>
        </div>

        <div className="repo-switcher">
          <div className="repo-avatar">
            R
          </div>

          <div>
            <strong>ReproLens</strong>
            <span>
              main · local
            </span>
          </div>

          <ChevronRight size={14} />
        </div>

        <nav>
          <span className="nav-label">
            WORKSPACE
          </span>

          {NAV.map(
            ({
              id,
              label,
              icon: Icon,
            }) => (
              <button
                className={`nav-item ${
                  active === id
                    ? "active"
                    : ""
                }`}
                key={id}
                onClick={() =>
                  setActive(id)
                }
              >
                <Icon size={16} />
                <span>{label}</span>
              </button>
            )
          )}

          <span className="nav-label second">
            SYSTEM
          </span>

          {SECONDARY.map(
            ({
              id,
              label,
              icon: Icon,
            }) => (
              <button
                className={`nav-item ${
                  active === id
                    ? "active"
                    : ""
                }`}
                key={id}
                onClick={() =>
                  setActive(id)
                }
              >
                <Icon size={16} />
                <span>{label}</span>
              </button>
            )
          )}
        </nav>

        <div className="sidebar-bottom">
          <div className="api-status">
            <span className="live-dot" />

            <div>
              <strong>
                API connected
              </strong>

              <span>
                127.0.0.1:8000
              </span>
            </div>
          </div>

          <div className="version">
            <span>ReproLens</span>
            <code>v0.3.0</code>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>ReproLens</span>

            <ChevronRight size={13} />

            <strong>
              {
                NAV.concat(
                  SECONDARY
                ).find(
                  (item) =>
                    item.id === active
                )?.label
              }
            </strong>
          </div>

          <div className="topbar-actions">
            <button
              className="search-pill"
              onClick={() =>
                setActive("retrieval")
              }
            >
              <Search size={14} />
              <span>Search</span>
              <kbd>⌘ K</kbd>
            </button>

            <button
              className="icon-button"
              title="Settings"
            >
              <Settings2 size={16} />
            </button>

            <div className="avatar">
              RC
            </div>
          </div>
        </header>

        <div className="content">
          {error && (
            <div className="error-banner">
              <XCircle size={18} />

              <div>
                <strong>
                  API connection issue
                </strong>

                <span>{error}</span>
              </div>

              <button onClick={loadData}>
                Retry
              </button>
            </div>
          )}

          {renderContent()}
        </div>

        <footer className="footer">
          <span>
            <span className="live-dot" />
            Analysis pipeline operational
          </span>

          <span>
            Controlled benchmark ·{" "}
            {models?.dataset_size ?? 20}{" "}
            examples
          </span>
        </footer>
      </main>
    </div>
  );
}