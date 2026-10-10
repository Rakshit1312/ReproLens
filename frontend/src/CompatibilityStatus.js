import { createElement } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  CircleDot,
} from "lucide-react";

const STATUS_PRESENTATION = {
  unknown: {
    icon: CircleDot,
    label: "not compared",
    tableClass: "neutral",
    signalClass: "signal-neutral",
  },
  mismatch: {
    icon: AlertTriangle,
    label: "mismatch",
    tableClass: "warning",
    signalClass: "signal-bad",
  },
  compatible: {
    icon: CheckCircle2,
    label: "compatible",
    tableClass: "success",
    signalClass: "signal-good",
  },
  not_applicable: {
    icon: CircleDot,
    label: "not applicable",
    tableClass: "neutral",
    signalClass: "signal-neutral",
  },
};

export function CompatibilityStatus({ status, variant = "table" }) {
  const presentation =
    STATUS_PRESENTATION[status] || STATUS_PRESENTATION.unknown;
  const className =
    variant === "signal"
      ? presentation.signalClass
      : `table-status ${presentation.tableClass}`;

  return createElement(
    "span",
    { className },
    createElement(presentation.icon, { size: 13 }),
    presentation.label
  );
}
