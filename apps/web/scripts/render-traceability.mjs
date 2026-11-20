#!/usr/bin/env node
// Renders the canonical P1 traceability data into Markdown and CSV.
// The JSON files are the single source of truth; do not edit the generated
// Markdown or CSV tables by hand.
import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..", "..");
const traceDir = join(repoRoot, "docs", "traceability");

const STATUS_LABEL = {
  PUBLISHED: "منتشرشده / Published",
  IMPLEMENTED: "پیاده‌سازی‌شده / Implemented",
  PARTIAL: "جزئی / Partial",
  PLANNED: "برنامه‌ریزی‌شده / Planned",
  CUBI_OWNED: "مخصوص CUBI / CUBI-owned",
  LEGAL: "حقوقی / Legal",
};

function load(name) {
  return JSON.parse(readFileSync(join(traceDir, name), "utf8"));
}

function escapeCell(value) {
  return String(value).replaceAll("|", "\\|").replaceAll("\n", " ");
}

function helpCell(row) {
  if (!row.help) return row.helpRationale ? escapeCell(row.helpRationale) : "—";
  const label = `[${row.help.title}](${row.help.url})`;
  return row.help.pdfPage ? `${label}, p. ${row.help.pdfPage}` : label;
}

function renderMatrix(meta, rows) {
  const lines = [];
  lines.push(`# ${meta.title}`);
  lines.push("");
  lines.push(`**Help baseline:** ${meta.baseline}`);
  lines.push(`**Rows:** ${rows.length} · **Generated from:** \`docs/traceability/${meta.file}\``);
  lines.push("");
  lines.push(meta.intro);
  lines.push("");
  lines.push("## Status legend");
  lines.push("");
  for (const [key, label] of Object.entries(STATUS_LABEL)) {
    lines.push(`- \`${key}\` — ${label}`);
  }
  lines.push("");
  lines.push("## Per-page traceability");
  lines.push("");
  lines.push("| ID | Page | Surface | Help topic | PDF | CUBI evidence | Status |");
  lines.push("|---|---|---|---|---|---|---|");
  for (const row of rows) {
    lines.push(
      `| ${row.id} | \`${row.page}\` | ${escapeCell(row.surface)} | ${helpCell(row)} | ${
        row.help?.pdfPage ?? "—"
      } | \`${row.evidence}\` | ${row.status} |`,
    );
  }
  lines.push("");
  lines.push("## Behaviour notes");
  lines.push("");
  for (const row of rows) {
    lines.push(`- **${row.id}** — ${row.cubiBehavior}`);
  }
  lines.push("");
  return lines.join("\n");
}

function toCsv(rows) {
  const header = [
    "id",
    "environment",
    "kind",
    "page",
    "surface",
    "module",
    "help_source",
    "help_title",
    "help_url",
    "help_pdf_page",
    "help_rationale",
    "cubi_behavior",
    "evidence",
    "status",
  ];
  const escape = (value) => {
    const text = value == null ? "" : String(value);
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  const lines = [header.join(",")];
  for (const row of rows) {
    lines.push(
      [
        row.id,
        row.environment,
        row.kind,
        row.page,
        row.surface,
        row.module,
        row.help?.source,
        row.help?.title,
        row.help?.url,
        row.help?.pdfPage,
        row.helpRationale,
        row.cubiBehavior,
        row.evidence,
        row.status,
      ]
        .map(escape)
        .join(","),
    );
  }
  return `${lines.join("\n")}\n`;
}

const engineering = load("engineering-v26.json");
const enterprise = load("enterprise-v26.json");

const engMeta = {
  title: "CUBI Engineering — P6 Professional V26 per-page traceability",
  baseline: engineering.baseline,
  file: "engineering-v26.json",
  intro:
    "Every public English route and every CUBI Engineering workspace window is listed here. " +
    "The Help column cites the official HTML Help topic; the PDF column cites the same topic in the " +
    "815-page Help PDF. `CUBI-owned` and `Legal` rows intentionally have no Oracle topic. " +
    "This document is internal traceability: no Oracle, Primavera or P6 name may appear in customer-facing UI.",
};
const entMeta = {
  title: "CUBI Enterprise — P6 EPPM V26 per-page traceability",
  baseline: enterprise.baseline,
  file: "enterprise-v26.json",
  intro:
    "Every CUBI Enterprise page is mapped to its P6 EPPM V26 Help topic and to an owning canonical module. " +
    "The EPPM Help set is HTML-only; it has no page-numbered PDF baseline. " +
    "This document is internal traceability: no Oracle, Primavera or P6 name may appear in customer-facing UI.",
};

writeFileSync(join(traceDir, "CUBI_ENGINEERING_V26_TRACEABILITY.md"), renderMatrix(engMeta, engineering.rows));
writeFileSync(join(traceDir, "CUBI_ENTERPRISE_V26_TRACEABILITY.md"), renderMatrix(entMeta, enterprise.rows));
writeFileSync(join(traceDir, "cubi-engineering-v26.csv"), toCsv(engineering.rows));
writeFileSync(join(traceDir, "cubi-enterprise-v26.csv"), toCsv(enterprise.rows));

console.log(
  `rendered ${engineering.rows.length} engineering rows and ${enterprise.rows.length} enterprise rows`,
);
