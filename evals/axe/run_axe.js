#!/usr/bin/env node
/**
 * Oracle #2. Run axe-core over a fixture and print its violations as JSON.
 *
 *   node run_axe.js path/to/fixture.html
 *
 * Prints {"available": true, "axe_version": "...", "violations": [...]} on
 * success, or {"available": false, "reason": "..."} with exit code 0 when the
 * pathway cannot run. A missing dependency is NOT a crash: the generator has to
 * be able to record that this domain went unchecked, in the same way the skills
 * record `Not reviewed` rather than `Clear`. A harness that dies here would
 * instead tempt the caller into emitting a contrast-only manifest that looks
 * complete.
 *
 * jsdom, not headless Chrome: no browser is installed, and determinism is the
 * whole premise. The cost is that rules needing layout or a computed cascade
 * cannot be evaluated — which is exactly why the rule set is a vetted
 * allow-list in owners.json rather than "whatever axe ships".
 */

const fs = require("fs");
const path = require("path");

function fail(reason) {
  process.stdout.write(JSON.stringify({ available: false, reason }, null, 2) + "\n");
  process.exit(0);
}

const target = process.argv[2];
if (!target) fail("no fixture path given");
if (!fs.existsSync(target)) fail(`fixture not found: ${target}`);

let JSDOM, axe, owners;
try {
  ({ JSDOM } = require("jsdom"));
} catch (e) {
  fail("jsdom is not installed — run `npm install` in evals/");
}
try {
  owners = JSON.parse(
    fs.readFileSync(path.join(__dirname, "owners.json"), "utf8")
  );
} catch (e) {
  fail(`owners.json unreadable: ${e.message}`);
}

const html = fs.readFileSync(target, "utf8");

// jsdom logs unimplemented-feature noise (canvas, layout) to the virtual
// console. Swallowed deliberately: it is not harness output and must never be
// mistaken for a finding.
const { VirtualConsole } = require("jsdom");
const dom = new JSDOM(html, {
  pretendToBeVisual: true,
  virtualConsole: new VirtualConsole(),
});

// axe-core captures these at load, so they must exist BEFORE it is required.
// Required in the other order it throws "Required window or document globals
// not defined" — which looks like a fixture problem and is not.
global.window = dom.window;
global.document = dom.window.document;
global.Node = dom.window.Node;
global.Element = dom.window.Element;
global.HTMLElement = dom.window.HTMLElement;
global.NodeList = dom.window.NodeList;

try {
  axe = require("axe-core");
} catch (e) {
  fail("axe-core is not installed — run `npm install` in evals/");
}

const allowed = Object.keys(owners.rules);

axe
  .run(dom.window.document, {
    runOnly: { type: "rule", values: allowed },
    resultTypes: ["violations"],
  })
  .then((result) => {
    const violations = [];
    for (const v of result.violations) {
      const rule = owners.rules[v.id];
      if (!rule) continue; // belt and braces; runOnly should have excluded it
      for (const node of v.nodes) {
        violations.push({
          rule: v.id,
          impact: v.impact,
          selector: Array.isArray(node.target) ? node.target.join(" ") : String(node.target),
          accepted_owners: rule.accepted_owners,
          one_root_cause: Boolean(rule.one_root_cause),
        });
      }
    }
    process.stdout.write(
      JSON.stringify(
        {
          available: true,
          axe_version: axe.version,
          rules_run: allowed,
          violations,
        },
        null,
        2
      ) + "\n"
    );
  })
  .catch((e) => fail(`axe.run failed: ${e.message}`));
