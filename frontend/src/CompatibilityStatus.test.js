import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { CompatibilityStatus } from "./CompatibilityStatus.js";

test("dashboard status renders unknown, compatible, and mismatch distinctly", () => {
  const renderStatus = (status) =>
    renderToStaticMarkup(
      createElement(CompatibilityStatus, { status })
    );

  const unknown = renderStatus("unknown");
  const notApplicable = renderStatus("not_applicable");
  const compatible = renderStatus("compatible");
  const mismatch = renderStatus("mismatch");

  assert.match(unknown, /table-status neutral/);
  assert.match(unknown, /not compared/);
  assert.match(notApplicable, /table-status neutral/);
  assert.match(notApplicable, /not applicable/);
  assert.notEqual(notApplicable, unknown);
  assert.match(compatible, /table-status success/);
  assert.match(compatible, /compatible/);
  assert.match(mismatch, /table-status warning/);
  assert.match(mismatch, /mismatch/);
});
