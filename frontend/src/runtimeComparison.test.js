import assert from "node:assert/strict";
import test from "node:test";

import {
  buildRuntimeComparisonRows,
  runtimeComparisonStatus,
} from "./runtimeComparison.js";

test("runtime rows keep observed versions separate from declarations", () => {
  const rows = buildRuntimeComparisonRows(
    {
      source: { type: "repository" },
      runtimes: {},
      runtime_declarations: { python: { value: "3.12" } },
      requirements: { python: { value: ">=3.11" } },
    },
    {
      source: { type: "ci" },
      runtimes: {},
      runtime_declarations: { python: { value: "3.11" } },
    },
    {
      python_declaration_version_match: 0,
      python_requirement_violation: 0,
    }
  );

  assert.deepEqual(rows[0], {
    label: "Observed runtime versions",
    dev: "Not observed",
    ci: "Not observed",
    status: "unknown",
  });
  assert.equal(rows[1].dev, "Python 3.12");
  assert.equal(rows[1].ci, "Python 3.11");
  assert.equal(rows[1].status, "mismatch");
  assert.equal(rows[2].dev, "Python >=3.11");
  assert.equal(rows[2].ci, "Python 3.11 (declared)");
  assert.equal(rows[2].status, "compatible");
  assert.equal(
    runtimeComparisonStatus({
      python_declaration_version_match: 0,
      python_requirement_violation: 0,
    }),
    "mismatch"
  );
});

test("missing comparable runtime features are not called compatible", () => {
  const rows = buildRuntimeComparisonRows(
    { source: { type: "repository" }, runtime_declarations: {} },
    { source: { type: "ci" }, runtime_declarations: {} },
    {}
  );

  assert.equal(rows[0].status, "unknown");
  assert.equal(rows[1].status, "unknown");
  assert.equal(rows[2].status, "unknown");
  assert.equal(runtimeComparisonStatus({}), "unknown");
});

test("schema 1.0 repository and CI runtimes remain declarations", () => {
  const rows = buildRuntimeComparisonRows(
    {
      schema_version: "1.0",
      source: { type: "repository" },
      runtimes: { node: { value: "20" } },
    },
    {
      schema_version: "1.0",
      source: { type: "ci" },
      runtimes: { node: { value: "18" } },
    },
    { node_declaration_version_match: 0 }
  );

  assert.equal(rows[0].dev, "Not observed");
  assert.equal(rows[1].dev, "Node 20");
  assert.equal(rows[1].ci, "Node 18");
  assert.equal(rows[1].status, "mismatch");
});
