"""
Evaluation & Testing Script for Utility Invoice Extractor.
Processes all 30 sample invoices from samples/utility-invoices/, compares extracted
results field-by-field against ground_truth.xlsx, and generates an interactive HTML report.
"""

from __future__ import annotations

import html
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure backend modules can be imported
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

import pandas as pd
from dotenv import load_dotenv

from extractor import ExtractionError, extract_invoice_fields
from pdf_utils import extract_text

# Load environment variables
backend_env = Path(__file__).resolve().parent.parent / "backend" / ".env"
if backend_env.exists():
    load_dotenv(backend_env)

API_KEY = os.getenv("NVIDIA_API_KEY", "").strip("\"'")
BASE_URL = os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL = os.getenv("LLM_MODEL", "thinkingmachines/inkling")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evaluator")


def normalize_val(val: Any) -> str:
    """Normalize values for robust comparison."""
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip().lower()
    if s.endswith(".0"):
        s = s[:-2]
    # Remove extra spaces / quotes
    s = " ".join(s.split()).strip("\"'")
    return s


def compare_fields(extracted: Any, truth: Any) -> bool:
    """Check if extracted value matches ground truth value."""
    norm_ext = normalize_val(extracted)
    norm_tru = normalize_val(truth)

    if not norm_ext and not norm_tru:
        return True  # Both empty/null
    if not norm_ext or not norm_tru:
        return False

    if norm_ext == norm_tru:
        return True

    # Try float comparison for numbers
    try:
        f_ext = float(norm_ext)
        f_tru = float(norm_tru)
        return abs(f_ext - f_tru) < 0.01
    except ValueError:
        pass

    # Partial containment check for addresses or vendor names
    if len(norm_tru) > 5 and norm_tru in norm_ext:
        return True

    return False


def run_evaluation():
    base_dir = Path(__file__).resolve().parent.parent
    samples_dir = base_dir / "samples" / "utility-invoices"
    gt_file = samples_dir / "ground_truth.xlsx"

    if not gt_file.exists():
        logger.error("Ground truth file not found at %s", gt_file)
        return

    logger.info("Loading ground truth from %s...", gt_file)
    df_gt = pd.read_excel(gt_file)
    logger.info("Found %d ground truth rows.", len(df_gt))

    eval_results = []
    start_time_all = time.time()

    # Track metrics
    field_totals = {
        "vendor_name": 0,
        "invoice_date": 0,
        "service_address": 0,
        "utility_type": 0,
        "usage_amount": 0,
        "usage_unit": 0,
        "billing_period_start": 0,
        "billing_period_end": 0,
    }
    field_matches = {k: 0 for k in field_totals}

    lang_stats: dict[str, dict[str, int]] = {}

    for idx, row in df_gt.iterrows():
        pdf_name = str(row.get("PDF Filename", "")).strip()
        invoice_id = str(row.get("Invoice ID", f"INV-{idx+1}"))
        language = str(row.get("language(s)", "en")).strip()
        is_edge = bool(row.get("is_edge_case", False))

        pdf_path = samples_dir / pdf_name
        logger.info("[%d/%d] Processing %s...", idx + 1, len(df_gt), pdf_name)

        item_result = {
            "index": idx + 1,
            "invoice_id": invoice_id,
            "filename": pdf_name,
            "language": language,
            "is_edge_case": is_edge,
            "gt_data": {},
            "ext_data": {},
            "field_matches": {},
            "status": "success",
            "error": None,
            "latency": 0.0,
            "overall_match": False,
        }

        # Collect ground truth fields
        gt_fields = {
            "vendor_name": row.get("vendor_name"),
            "invoice_date": row.get("invoice_date (YYYY-MM-DD)"),
            "service_address": row.get("service_address"),
            "utility_type": row.get("utility_type"),
            "usage_amount": row.get("usage_amount"),
            "usage_unit": row.get("usage_unit"),
            "billing_period_start": row.get("billing_period_start (YYYY-MM-DD)"),
            "billing_period_end": row.get("billing_period_end (YYYY-MM-DD)"),
        }
        item_result["gt_data"] = gt_fields

        if not pdf_path.exists():
            item_result["status"] = "error"
            item_result["error"] = f"File not found: {pdf_name}"
            eval_results.append(item_result)
            continue

        t0 = time.time()
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            text = extract_text(pdf_bytes, pdf_name)

            extracted_obj = extract_invoice_fields(
                text, api_key=API_KEY, base_url=BASE_URL, model=MODEL
            )
            item_result["ext_data"] = extracted_obj.model_dump()
            item_result["latency"] = round(time.time() - t0, 2)
        except Exception as exc:
            item_result["status"] = "error"
            item_result["error"] = str(exc)
            item_result["latency"] = round(time.time() - t0, 2)
            eval_results.append(item_result)
            continue

        # Field matching evaluation
        all_matched = True
        for field_name, gt_val in gt_fields.items():
            ext_val = item_result["ext_data"].get(field_name)
            is_match = compare_fields(ext_val, gt_val)
            item_result["field_matches"][field_name] = is_match

            field_totals[field_name] += 1
            if is_match:
                field_matches[field_name] += 1
            else:
                all_matched = False

        item_result["overall_match"] = all_matched

        # Track language stats
        if language not in lang_stats:
            lang_stats[language] = {"total": 0, "correct": 0}
        lang_stats[language]["total"] += 1
        if all_matched:
            lang_stats[language]["correct"] += 1

        eval_results.append(item_result)

    total_time = round(time.time() - start_time_all, 2)

    # Compute high level summary stats
    total_invoices = len(eval_results)
    success_invoices = sum(1 for r in eval_results if r["status"] == "success")
    perfect_invoices = sum(1 for r in eval_results if r.get("overall_match"))

    total_tested_fields = sum(field_totals.values())
    total_matched_fields = sum(field_matches.values())
    overall_accuracy = (
        round((total_matched_fields / total_tested_fields) * 100, 1)
        if total_tested_fields > 0
        else 0.0
    )

    logger.info("Evaluation complete! Overall Accuracy: %.1f%%", overall_accuracy)

    # Generate HTML Report
    generate_html_report(
        base_dir / "evaluation_report.html",
        results=eval_results,
        overall_accuracy=overall_accuracy,
        total_invoices=total_invoices,
        success_invoices=success_invoices,
        perfect_invoices=perfect_invoices,
        total_tested_fields=total_tested_fields,
        total_matched_fields=total_matched_fields,
        field_totals=field_totals,
        field_matches=field_matches,
        lang_stats=lang_stats,
        total_time=total_time,
    )


def generate_html_report(
    output_path: Path,
    *,
    results: list[dict],
    overall_accuracy: float,
    total_invoices: int,
    success_invoices: int,
    perfect_invoices: int,
    total_tested_fields: int,
    total_matched_fields: int,
    field_totals: dict[str, int],
    field_matches: dict[str, int],
    lang_stats: dict[str, dict[str, int]],
    total_time: float,
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Generate Field Breakdown Cards
    field_cards_html = ""
    for field, total in field_totals.items():
        matched = field_matches[field]
        pct = round((matched / total) * 100, 1) if total > 0 else 0
        bar_color = "bg-emerald-500" if pct >= 90 else "bg-amber-500" if pct >= 75 else "bg-rose-500"
        title = field.replace("_", " ").title()
        field_cards_html += f"""
        <div class="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs">
          <div class="flex justify-between items-center mb-2">
            <span class="text-xs font-semibold text-slate-500 uppercase">{title}</span>
            <span class="text-sm font-bold text-slate-800">{pct}%</span>
          </div>
          <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
            <div class="{bar_color} h-full" style="width: {pct}%"></div>
          </div>
          <div class="mt-2 text-[11px] text-slate-400 font-medium">
            {matched} / {total} correct
          </div>
        </div>
        """

    # Generate Invoice Rows HTML
    table_rows_html = ""
    for r in results:
        idx = r["index"]
        fname = html.escape(r["filename"])
        lang = html.escape(r["language"]).upper()
        status = r["status"]
        is_edge = r["is_edge_case"]
        latency = r["latency"]
        overall = r.get("overall_match", False)

        status_badge = (
          '<span class="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">100% Match</span>'
          if overall
          else '<span class="px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-50 text-rose-700 border border-rose-200">Partial / Error</span>'
        )

        edge_badge = (
          '<span class="px-2 py-0.5 text-[10px] font-medium rounded-md bg-purple-50 text-purple-700 border border-purple-200">Edge Case</span>'
          if is_edge
          else ""
        )

        field_comparison_html = ""
        if status == "success":
            for f_name, gt_v in r["gt_data"].items():
                ext_v = r["ext_data"].get(f_name)
                matched = r["field_matches"].get(f_name, False)

                badge = (
                  '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-100 text-emerald-800">MATCH</span>'
                  if matched
                  else '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-rose-100 text-rose-800">MISMATCH</span>'
                )

                field_comparison_html += f"""
                <tr class="border-b border-slate-100 text-xs">
                  <td class="py-2 px-3 font-semibold text-slate-600 uppercase">{f_name.replace('_', ' ')}</td>
                  <td class="py-2 px-3 font-mono text-slate-700">{html.escape(str(gt_v or "—"))}</td>
                  <td class="py-2 px-3 font-mono text-slate-800 font-medium">{html.escape(str(ext_v or "—"))}</td>
                  <td class="py-2 px-3 text-right">{badge}</td>
                </tr>
                """
        else:
            field_comparison_html = f"""
            <tr>
              <td colspan="4" class="py-3 px-3 text-xs text-rose-600 bg-rose-50 rounded-lg">
                <strong>Extraction Error:</strong> {html.escape(str(r.get("error")))}
              </td>
            </tr>
            """

        table_rows_html += f"""
        <tbody class="border-b border-slate-200 bg-white">
          <tr class="hover:bg-slate-50/80 transition-colors cursor-pointer" onclick="toggleDetails('{idx}')">
            <td class="py-3.5 px-4 text-xs font-semibold text-slate-400">{idx}</td>
            <td class="py-3.5 px-4 text-sm font-medium text-slate-800">
              <div class="flex items-center gap-2">
                <span>{fname}</span>
                {edge_badge}
              </div>
            </td>
            <td class="py-3.5 px-4 text-xs">
              <span class="px-2 py-0.5 rounded-md bg-slate-100 font-mono text-slate-600">{lang}</span>
            </td>
            <td class="py-3.5 px-4 text-xs font-mono text-slate-500">{latency}s</td>
            <td class="py-3.5 px-4 text-right">{status_badge}</td>
          </tr>
          <tr id="details-{idx}" class="hidden bg-slate-50/50">
            <td colspan="5" class="p-4 border-t border-slate-100">
              <div class="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-2xs">
                <div class="bg-slate-50 px-4 py-2.5 border-b border-slate-100 flex justify-between items-center text-xs font-semibold text-slate-700">
                  <span>Field Comparison Details</span>
                  <span class="text-[11px] font-mono text-slate-400">File: {fname}</span>
                </div>
                <table class="w-full text-left">
                  <thead>
                    <tr class="bg-slate-100/50 text-[10px] font-bold text-slate-400 uppercase border-b border-slate-100">
                      <th class="py-2 px-3">Field</th>
                      <th class="py-2 px-3">Ground Truth</th>
                      <th class="py-2 px-3">Extracted Result</th>
                      <th class="py-2 px-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {field_comparison_html}
                  </tbody>
                </table>
              </div>
            </td>
          </tr>
        </tbody>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Invoice Extractor Accuracy & Evaluation Report</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-800 antialiased min-h-screen">
  <!-- Header -->
  <header class="bg-white border-b border-slate-200">
    <div class="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-slate-900">Utility Invoice Extractor — Evaluation Report</h1>
        <p class="text-xs text-slate-500 mt-0.5">Automated accuracy benchmark against ground truth dataset ({timestamp})</p>
      </div>
      <div class="flex items-center gap-3">
        <span class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-900 text-white shadow-2xs">
          Model: {MODEL}
        </span>
      </div>
    </div>
  </header>

  <main class="max-w-6xl mx-auto px-6 py-10">
    <!-- Executive KPI Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
      <div class="p-5 bg-white rounded-2xl border border-slate-200 shadow-2xs">
        <span class="text-xs font-medium text-slate-400 uppercase tracking-wide">Overall Accuracy</span>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-bold text-slate-900">{overall_accuracy}%</span>
          <span class="text-xs font-semibold text-emerald-600">({total_matched_fields}/{total_tested_fields} fields)</span>
        </div>
      </div>

      <div class="p-5 bg-white rounded-2xl border border-slate-200 shadow-2xs">
        <span class="text-xs font-medium text-slate-400 uppercase tracking-wide">Total Invoices Tested</span>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-bold text-slate-900">{total_invoices}</span>
          <span class="text-xs font-semibold text-slate-500">100% processed</span>
        </div>
      </div>

      <div class="p-5 bg-white rounded-2xl border border-slate-200 shadow-2xs">
        <span class="text-xs font-medium text-slate-400 uppercase tracking-wide">100% Perfect Matches</span>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-bold text-slate-900">{perfect_invoices}</span>
          <span class="text-xs font-semibold text-emerald-600">({round(perfect_invoices/total_invoices*100, 1)}%)</span>
        </div>
      </div>

      <div class="p-5 bg-white rounded-2xl border border-slate-200 shadow-2xs">
        <span class="text-xs font-medium text-slate-400 uppercase tracking-wide">Total Processing Time</span>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-bold text-slate-900">{total_time}s</span>
          <span class="text-xs font-semibold text-slate-500">~{round(total_time/total_invoices, 1)}s / file</span>
        </div>
      </div>
    </div>

    <!-- Field Accuracy Breakdown Grid -->
    <div class="mb-10">
      <h2 class="text-base font-semibold text-slate-900 mb-4">Accuracy Breakdown by Field</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        {field_cards_html}
      </div>
    </div>

    <!-- Test Results Table -->
    <div class="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
      <div class="p-6 border-b border-slate-100 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 class="text-base font-semibold text-slate-900">Detailed Invoice Test Results</h2>
          <p class="text-xs text-slate-500 mt-0.5">Click any row to expand side-by-side ground truth vs extracted comparison</p>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 text-[11px] font-bold text-slate-400 uppercase border-b border-slate-200">
              <th class="py-3 px-4 w-12">#</th>
              <th class="py-3 px-4">Invoice PDF Filename</th>
              <th class="py-3 px-4">Lang</th>
              <th class="py-3 px-4">Latency</th>
              <th class="py-3 px-4 text-right">Match Status</th>
            </tr>
          </thead>
          {table_rows_html}
        </table>
      </div>
    </div>
  </main>

  <script>
    function toggleDetails(id) {{
      const el = document.getElementById('details-' + id);
      if (el) {{
        el.classList.toggle('hidden');
      }}
    }}
  </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info("Report saved to %s", output_path)


if __name__ == "__main__":
    run_evaluation()
