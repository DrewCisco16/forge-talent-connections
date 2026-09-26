#!/usr/bin/env node
// Copy and wall scan for any file, including the ones the Flutter suite never
// reads (index.html, web/, docs, the agent layer).
//
// The rules are NOT restated here. They are read at runtime from the Dart
// tests that own them, so this tool can never drift from the suite:
//   test/copy/walled_repo_test.dart     internal names and filing identifiers
//                                       (stored base64 there; decoded only in
//                                       memory here and never printed)
//   test/copy/product_language_test.dart recruiting vocabulary (--copy only)
// The typography rule (no em or en dashes, including their HTML entities) is
// the house rule from test/copy/no_em_dash_test.dart.
//
// Usage:  node .claude/tools/scan-copy.mjs [--copy] [--root DIR] <file>...
// Exit:   0 clean, 1 findings, 2 could not run (a rule source is missing,
//         unreadable, or malformed, or a file could not be read as text).
//         Fail closed: a scan that could not load its rules or read a file
//         never reports clean.

import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");

const WALLED_SOURCE = "test/copy/walled_repo_test.dart";
const LANGUAGE_SOURCE = "test/copy/product_language_test.dart";

// Built from code points so this file never contains the characters it bans.
const DASHES = [
  { char: String.fromCharCode(0x2014), name: "em dash" },
  { char: String.fromCharCode(0x2013), name: "en dash" },
];
const DASH_ENTITY = /&(?:(mdash)|(ndash));|&#0*(?:(8212)|(8211));|&#x0*(?:(2014)|(2013));/gi;
const BASE64 = /^[A-Za-z0-9+/_-]+={0,2}$/;

export class RuleSourceError extends Error {}

function readRuleSource(relPath, root) {
  try {
    return readFileSync(join(root, relPath), "utf8");
  } catch (err) {
    throw new RuleSourceError(`cannot read rule source ${relPath}: ${err.code ?? err.message}`);
  }
}

/** Decoded walled terms, upper-cased, exactly as the Dart guard compares them. */
export function loadWalledTerms(root = REPO_ROOT) {
  const src = readRuleSource(WALLED_SOURCE, root);
  const open = src.indexOf("_banned = <String>[");
  const close = open === -1 ? -1 : src.indexOf("]", open);
  if (open === -1 || close === -1) {
    throw new RuleSourceError(`${WALLED_SOURCE}: banned list not found`);
  }
  // Every quoted entry, whatever its alphabet. An entry this tool cannot
  // decode stops the scan: dropping it silently would scan that term CLEAN.
  const entries = [...src.slice(open, close).matchAll(/"([^"]*)"|'([^']*)'/g)].map((m) => m[1] ?? m[2]);
  if (entries.length === 0) {
    throw new RuleSourceError(`${WALLED_SOURCE}: banned list is empty`);
  }
  return entries.map((e, i) => {
    if (!BASE64.test(e)) throw new RuleSourceError(`${WALLED_SOURCE}: entry #${i + 1} is not base64`);
    const term = Buffer.from(e.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8");
    if (!term.trim()) throw new RuleSourceError(`${WALLED_SOURCE}: entry #${i + 1} decodes to nothing`);
    return term.toUpperCase();
  });
}

/** The recruiting vocabulary list from the product-language test. */
export function loadRecruitingWords(root = REPO_ROOT) {
  const src = readRuleSource(LANGUAGE_SOURCE, root);
  const open = src.indexOf("_bannedWords = <String>[");
  const close = open === -1 ? -1 : src.indexOf("];", open);
  if (open === -1 || close === -1) {
    throw new RuleSourceError(`${LANGUAGE_SOURCE}: banned word list not found`);
  }
  const words = [...src.slice(open, close).matchAll(/"([a-z]+)"/g)].map((m) => m[1]);
  if (words.length === 0) {
    throw new RuleSourceError(`${LANGUAGE_SOURCE}: banned word list is empty`);
  }
  return words;
}

/**
 * Text from a file's bytes, or null when it is not text this tool can read.
 * A byte-order mark selects UTF-16 or UTF-8; NUL bytes without one mean an
 * encoding the scan would misread, which must not pass as clean.
 */
export function decodeText(buf) {
  if (buf.length >= 2 && buf[0] === 0xff && buf[1] === 0xfe) return buf.subarray(2).toString("utf16le");
  if (buf.length >= 2 && buf[0] === 0xfe && buf[1] === 0xff) {
    const le = Buffer.from(buf.subarray(2));
    le.swap16();
    return le.toString("utf16le");
  }
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) return buf.subarray(3).toString("utf8");
  if (buf.includes(0)) return null;
  return buf.toString("utf8");
}

// Embedded images are base64 noise; a word boundary inside one is not copy.
const DATA_URI = /data:[^"')\s]+/g;

/**
 * Scan text. Returns findings as {line, rule, detail}. Walled terms are
 * reported by index only; the decoded term never leaves memory.
 */
export function scanText(text, { path = "", walled = [], recruiting = null } = {}) {
  const findings = [];
  const upperPath = path.toUpperCase();
  walled.forEach((term, i) => {
    if (upperPath.includes(term)) {
      findings.push({ line: 0, rule: "walled-term", detail: `walled term #${i + 1} in file path` });
    }
  });
  const lines = text.split(/\r?\n/);
  lines.forEach((raw, idx) => {
    const line = idx + 1;
    for (const d of DASHES) {
      if (raw.includes(d.char)) findings.push({ line, rule: "dash", detail: d.name });
    }
    for (const m of raw.matchAll(DASH_ENTITY)) {
      findings.push({ line, rule: "dash", detail: `${m[1] || m[3] || m[5] ? "em" : "en"} dash (HTML entity)` });
    }
    const upper = raw.toUpperCase();
    walled.forEach((term, i) => {
      if (upper.includes(term)) {
        findings.push({ line, rule: "walled-term", detail: `walled term #${i + 1}` });
      }
    });
    if (recruiting) {
      const visible = raw.replace(DATA_URI, "");
      for (const word of recruiting) {
        if (new RegExp(`\\b${word}\\b`, "i").test(visible)) {
          findings.push({ line, rule: "recruiting-vocabulary", detail: `"${word}"` });
        }
      }
    }
  });
  return findings;
}

export function scanFiles(paths, { copy = false, root = REPO_ROOT } = {}) {
  const walled = loadWalledTerms(root);
  const recruiting = copy ? loadRecruitingWords(root) : null;
  const results = [];
  for (const p of paths) {
    // A path that itself holds a walled term is never printed.
    const walledIndex = walled.findIndex((t) => p.toUpperCase().includes(t));
    const shown = walledIndex === -1 ? p : `[path withheld: contains walled term #${walledIndex + 1}]`;
    let buf;
    try {
      buf = readFileSync(resolve(root, p));
    } catch (err) {
      results.push({ path: shown, line: 0, rule: "unreadable", detail: err.code ?? err.message });
      continue;
    }
    const text = decodeText(buf);
    if (text === null) {
      results.push({ path: shown, line: 0, rule: "unreadable", detail: "binary or unsupported encoding" });
      continue;
    }
    for (const f of scanText(text, { path: p, walled, recruiting })) results.push({ path: shown, ...f });
  }
  return results;
}

export function main(argv) {
  const copy = argv.includes("--copy");
  const rootAt = argv.indexOf("--root");
  if (rootAt !== -1 && !argv[rootAt + 1]) {
    console.error("usage: node .claude/tools/scan-copy.mjs [--copy] [--root DIR] <file>...");
    return 2;
  }
  const root = rootAt === -1 ? REPO_ROOT : resolve(argv[rootAt + 1]);
  // Only --root and its value are options; every other argument is a file.
  // (Excluding "rootAt + 1" when rootAt is -1 once dropped the first file.)
  const optionAt = new Set(rootAt === -1 ? [] : [rootAt, rootAt + 1]);
  const paths = argv.filter((a, i) => a !== "--copy" && !optionAt.has(i));
  if (paths.length === 0) {
    console.error("usage: node .claude/tools/scan-copy.mjs [--copy] [--root DIR] <file>...");
    return 2;
  }
  let results;
  try {
    results = scanFiles(paths, { copy, root });
  } catch (err) {
    if (err instanceof RuleSourceError) {
      console.error(`SCAN NOT RUN: ${err.message}`);
      return 2;
    }
    throw err;
  }
  for (const r of results) console.log(`${r.path}:${r.line}  ${r.rule}  ${r.detail}`);
  const unreadable = results.some((r) => r.rule === "unreadable");
  console.log(results.length === 0 ? `CLEAN: ${paths.length} file(s)` : `FINDINGS: ${results.length}`);
  if (unreadable) return 2;
  return results.length === 0 ? 0 : 1;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main(process.argv.slice(2));
}
