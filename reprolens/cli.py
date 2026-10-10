from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .diff import compare
from .extractor import (
    fingerprint_ci,
    fingerprint_local,
    fingerprint_repository,
)
from .orchestrator import analyze_repository
from .services.llm_service import (
    LLMConfigurationError,
    LLMProviderError,
    LLMTimeoutError,
)


def _value(section: dict, key: str):
    item = section.get(key)
    return item.get("value") if item else None


def print_analysis(result: dict) -> None:
    """Print a concise human-readable ReproLens analysis."""

    print()
    print("=" * 60)
    print("                 ReproLens Pre-CI Analysis")
    print("=" * 60)

    print(f"\nRepository: {result['repository']}")

    compatibility = result["compatibility"]
    features = compatibility.get("features", {})
    candidates = compatibility.get(
        "compatibility", {}
    ).get("candidates", [])

    prediction = result.get("prediction", {})

    print("\n[1] ENVIRONMENT")
    print("-" * 60)

    dev = result["development_fingerprint"]
    ci = result["ci_fingerprint"]

    dev_python = _value(
        dev.get("requirements", {}),
        "python",
    )

    ci_python = _value(
        ci.get("runtimes", {}),
        "python",
    )

    ci_runner = _value(
        ci.get("platform", {}),
        "ci_runner",
    )

    print(
        f"Development Python requirement : "
        f"{dev_python or 'unknown'}"
    )
    print(
        f"CI Python runtime              : "
        f"{ci_python or 'unknown'}"
    )
    print(
        f"CI runner                      : "
        f"{ci_runner or 'unknown'}"
    )

    difference_count = features.get(
        "environment_difference_count",
        0,
    )

    print(
        f"Environment differences        : "
        f"{difference_count}"
    )

    print("\n[2] COMPATIBILITY")
    print("-" * 60)

    if candidates:
        for candidate in candidates:
            print(
                f"- [{candidate['code']}] "
                f"{candidate['reason']} "
                f"({candidate['severity']})"
            )
    else:
        print(
            "No compatibility risk candidates "
            "detected from available metadata."
        )

    print("\n[3] PREDICTION")
    print("-" * 60)

    if prediction:
        risk = prediction.get(
            "risk_score",
            0,
        )

        label = (
            "HIGH RISK"
            if prediction.get("prediction") == 1
            else "LOW RISK"
        )

        print(f"Prediction : {label}")
        print(f"Risk score : {risk:.3f}")
        print(
            f"Threshold  : "
            f"{prediction.get('threshold', 0.5):.2f}"
        )

        print(
            "\nModel status: "
            f"{prediction.get('status', 'unknown')}"
        )

    print("\n[4] EVIDENCE")
    print("-" * 60)

    contexts = result.get(
        "retrieved_context",
        [],
    )

    print(
        f"Local repository evidence retrieved: "
        f"{len(contexts)}"
    )

    sourcegraph = result.get(
        "sourcegraph_results",
        []
    )

    print(
        f"Sourcegraph results: "
        f"{len(sourcegraph)}"
    )

    if contexts:
        print("\nTop retrieved context:")

        for context in contexts[:3]:
            print(
                f"- {context.get('source', 'unknown')}"
            )

    print("\n[5] RECOMMENDATION")
    print("-" * 60)

    if candidates:
        print(
            "Investigate the detected compatibility "
            "candidate(s) before CI execution."
        )
    elif prediction.get("prediction") == 1:
        print(
            "Review the repository and CI environment "
            "for potential incompatibilities."
        )
    else:
        print(
            "No immediate environment-induced risk "
            "was detected from available evidence."
        )

    explanation = result.get("explanation")
    if explanation:
        metadata = result.get("llm_metadata") or {}
        provider = metadata.get("provider", "configured provider")
        model = metadata.get("model", "configured model")
        print(f"\n[6] LLM EXPLANATION ({provider} / {model})")
        print("-" * 60)
        print(explanation)

    print("\n" + "=" * 60)
    print(
        "Note: prediction is currently a prototype "
        "benchmark-model signal."
    )
    print("=" * 60)
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="reprolens",
        description=(
            "ReproLens environment analysis "
            "and pre-CI risk prediction"
        ),
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    p = sub.add_parser(
        "fingerprint",
        help="Extract a repository fingerprint",
    )

    p.add_argument(
        "path",
        nargs="?",
        default=".",
    )

    p.add_argument(
        "--local",
        action="store_true",
        help="Fingerprint the actual local machine",
    )

    p.add_argument(
        "--ci",
        action="store_true",
        help="Extract the CI-side GitHub Actions fingerprint",
    )

    p.add_argument(
        "--output",
        "-o",
    )

    a = sub.add_parser(
        "analyze",
        help="Run the ReproLens analysis pipeline",
    )

    a.add_argument(
        "path",
        nargs="?",
        default=".",
    )

    a.add_argument(
        "--question",
        "-q",
    )

    a.add_argument(
        "--top-k",
        type=int,
        default=5,
    )

    a.add_argument(
        "--no-sourcegraph",
        action="store_true",
    )

    a.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON output",
    )

    a.add_argument(
        "--llm",
        action="store_true",
        help="Include an explanation from the configured LLM provider",
    )

    a.add_argument(
        "--output",
        "-o",
        help="Write the machine-readable analysis report to a file",
    )

    c = sub.add_parser(
        "compare",
        help="Compare two fingerprint JSON files",
    )

    c.add_argument("development")
    c.add_argument("ci")
    c.add_argument("--output", "-o")

    args = parser.parse_args()

    if args.command == "analyze":

        try:
            result = analyze_repository(
                args.path,
                question=args.question,
                top_k=args.top_k,
                use_sourcegraph=not args.no_sourcegraph,
                use_llm=args.llm,
            )
        except LLMConfigurationError:
            print(
                "reprolens: LLM configuration error. Check "
                "REPROLENS_LLM_PROVIDER, REPROLENS_LLM_MODEL, and "
                "REPROLENS_LLM_API_KEY.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
        except LLMTimeoutError:
            print(
                "reprolens: LLM request timed out. Check provider availability "
                "and REPROLENS_LLM_TIMEOUT, then retry.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
        except LLMProviderError:
            print(
                "reprolens: LLM provider failed or is unavailable. Check the "
                "configured endpoint and model, then retry.",
                file=sys.stderr,
            )
            raise SystemExit(2) from None

        if args.json or args.output:
            text = json.dumps(result, indent=2)
            if args.output:
                Path(args.output).write_text(
                    text + "\n",
                    encoding="utf-8",
                )
            else:
                print(text)
        else:
            print_analysis(result)

        return

    if args.command == "fingerprint":

        fp = (
            fingerprint_local()
            if args.local
            else fingerprint_ci(args.path)
            if args.ci
            else fingerprint_repository(args.path)
        )

        result = fp.to_dict()

    else:

        result = compare(
            json.loads(
                Path(args.development).read_text()
            ),
            json.loads(
                Path(args.ci).read_text()
            ),
        )

    text = json.dumps(
        result,
        indent=2,
    )

    if getattr(args, "output", None):
        Path(args.output).write_text(
            text + "\n",
            encoding="utf-8",
        )
    else:
        print(text)


if __name__ == "__main__":
    main()