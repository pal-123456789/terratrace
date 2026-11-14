/* TerraTrace deck — 10 slides, built on the same dark palette and the same real terrain
   data as the repository's cover image. Structured deck: theme + layouts + placeholders. */
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/sessions/intelligent-blissful-thompson/mnt/.claude/skills/pptx/scripts/apply_theme.js");

// Repository-relative, overridable, never absolute: the previous revision hard-coded this
// session's scratch directory, so nobody else could rebuild the deck at all. Regenerate the panels
// with `python scripts/make_deck_assets.py` (see that file — the imagery is the project's own DEMs).
const REPO_ROOT = require("path").resolve(__dirname, "..", "..");
const ASSETS = process.env.DECK_ASSETS || require("path").join(REPO_ROOT, "assets", "deck");
const OUT = require("path").join(__dirname, "..", "..", "TerraTrace-deck.pptx");

const THEME = {
  name: "TerraTrace Dark",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "EEF2F7",      // text1   — ink
    lt1: "05070C",      // background1 — deep space
    dk2: "6FD6C0",      // text2   — teal
    lt2: "0B1220",      // background2 — panel
    accent1: "6FD6C0",  // teal
    accent2: "E0913F",  // warm
    accent3: "2D4A55",
    accent4: "8C9AAD",  // muted
    accent5: "A9C9C6",
    accent6: "1D2634",  // rule
    hlink: "6FD6C0",
    folHlink: "8C9AAD",
  },
};

const INK = "EEF2F7", MUTE = "8C9AAD", ACC = "6FD6C0", WARM = "E0913F",
      RULE = "1D2634", PANEL = "0B1220", BG = "05070C";
const HEAD = "Cambria", BODY = "Calibri";
const M = 0.62, W = 13.33, H = 7.5;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Pal Ghevariya";
pres.title = "TerraTrace - Planetary Analog OS";
pres.subject = "Map-scale terrain-morphology analog screening across five worlds";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

/* ------------------------------------------------------------------ layouts */
function titlePlaceholder(size) {
  return [{ placeholder: { options: {
    name: "title", type: "title", x: M, y: 0.66, w: 12.1, h: 0.86,
    fontFace: HEAD, fontSize: size, bold: true, color: INK, align: "left", valign: "middle", margin: 0,
  }, text: "" } }];
}
function chrome() {
  return [
    { text: { text: "TerraTrace  ·  Planetary Analog OS", options: {
        x: M, y: 6.98, w: 6.0, h: 0.3, fontFace: BODY, fontSize: 10, color: MUTE, margin: 0, isTextBox: true } } },
  ];
}

pres.defineSlideMaster({ title: "COVER", background: { color: BG }, objects: [] });
pres.defineSlideMaster({
  title: "MAIN", background: { color: BG },
  objects: [...titlePlaceholder(32), ...chrome()],
  slideNumber: { x: 12.35, y: 6.98, w: 0.6, h: 0.3, color: MUTE, fontFace: BODY, fontSize: 10, align: "right" },
});
pres.defineSlideMaster({ title: "QUIET", background: { color: BG }, objects: [...chrome()] });

/* ------------------------------------------------------------------ helpers */
function kicker(slide, text) {
  slide.addText(text.toUpperCase(), {
    x: M, y: 0.38, w: 11.0, h: 0.26, fontFace: BODY, fontSize: 11, bold: true,
    color: ACC, charSpacing: 1.4, margin: 0, isTextBox: true,
  });
}
// `**bold**` in a hand-written string is a *typo waiting to happen*: pptxgenjs prints the
// asterisks literally (slide 2 shipped with "**which Earth terrains are morphologically
// comparable...**" on it), so inline emphasis is parsed here instead of being hoped for.
function inlineRuns(text, boldColor) {
  if (!text.includes("**")) return text;
  const runs = [];
  text.split("**").forEach((part, i) => {
    if (!part) return;
    runs.push(i % 2 === 1
      ? { text: part, options: { bold: true, color: boldColor || INK } }
      : { text: part, options: {} });
  });
  return runs.length ? runs : text;
}

function lede(slide, text, y, h, w, x) {
  slide.addText(inlineRuns(text), {
    x: x === undefined ? M : x, y: y, w: w || 12.1, h: h,
    fontFace: BODY, fontSize: 15, color: MUTE, lineSpacing: 22, margin: 0, isTextBox: true, valign: "top",
  });
}
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06, fill: { color: fill || PANEL },
    line: { color: RULE, width: 1 },
    shadow: { type: "outer", color: "000000", blur: 12, offset: 3, angle: 90, opacity: 0.35 },
  });
}
function stat(slide, x, y, w, value, label, color) {
  slide.addText(value, { x, y, w, h: 0.66, fontFace: HEAD, fontSize: 40, bold: true, color: color || ACC, margin: 0, isTextBox: true, align: "left" });
  slide.addText(label, { x, y: y + 0.68, w, h: 0.62, fontFace: BODY, fontSize: 11.5, color: MUTE, margin: 0, isTextBox: true, align: "left", lineSpacing: 15 });
}
function panel(slide, file, x, y, w, h, caption, accent) {
  slide.addImage({ path: `${ASSETS}/${file}`, x, y, w, h, rounding: false });
  slide.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { type: "none" }, line: { color: RULE, width: 1 } });
  if (caption) slide.addText(caption, {
    x, y: y + h + 0.09, w, h: 0.3, fontFace: BODY, fontSize: 10.5, color: accent || MUTE, margin: 0, isTextBox: true });
}

pres.addSection({ title: "The question" });
/* ============================================================ 1 · cover ===== */
const s1 = pres.addSlide({ masterName: "COVER", sectionTitle: "The question" });
s1.addImage({ path: require("path").join(REPO_ROOT, "assets", "cover.png"), x: 0, y: 0, w: W, h: H });
s1.addText("github.com/pal-123456789/terratrace", { x: 0.62, y: 6.98, w: 6.0, h: 0.3, fontFace: "Courier New", fontSize: 11, color: ACC, margin: 0, isTextBox: true });

/* ========================================================= 2 · question ==== */
const s2 = pres.addSlide({ masterName: "MAIN", sectionTitle: "The question" });
kicker(s2, "NASA Space Apps Challenge 2026");
s2.addText("Earth terrain that answers to Mars and the Moon", { placeholder: "title" });

lede(s2, "TerraTrace asks one narrow, measurable question: **which Earth terrains are morphologically comparable to a given planetary reference, at a declared common spatial support?** It answers with measured distance, uncertainty and a gap ledger — and nothing else.", 1.72, 1.5, 7.5);

card(s2, M, 3.42, 7.5, 1.28);
s2.addText("Challenge", { x: M + 0.28, y: 3.58, w: 2.0, h: 0.26, fontFace: BODY, fontSize: 10.5, bold: true, color: WARM, charSpacing: 1.2, margin: 0, isTextBox: true });
s2.addText("“Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars”", {
  x: M + 0.28, y: 3.86, w: 6.95, h: 0.7, fontFace: HEAD, fontSize: 14.5, italic: true, color: INK, lineSpacing: 19, margin: 0, isTextBox: true });

lede(s2, "Published as open prior art, deliberately, weeks ahead of the event — stated openly rather than dressed up as event work.", 4.88, 0.6, 7.5);

panel(s2, "khaybar.png", 8.5, 1.72, 4.22, 4.22, "Harrat Khaybar, Saudi Arabia · σ 102 m · real Copernicus GLO-30 terrain", ACC);

pres.addSection({ title: "Method" });
/* ========================================================= 3 · pipeline ==== */
const s3 = pres.addSlide({ masterName: "MAIN", sectionTitle: "Method" });
kicker(s3, "Pipeline");
s3.addText("Real elevation to a defensible comparison", { placeholder: "title" });
lede(s3, "Five stages, each one a place where an analog study usually overclaims.", 1.62, 0.4, 12.1);

const steps = [
  ["01", "Catalog", "15 products with coverage, licence and vertical accuracy — body, CRS and datum asserted by tests."],
  ["02", "Support", "Each window reprojected onto its own body's metric grid. Nominal posting (30 m GLO-30, 463 m MOLA) is NOT the compared resolution: the common effective support is 3x source spacing, declared before the run."],
  ["03", "Describe", "40 cited descriptor families — ~290 scalar values — computed in pure NumPy."],
  ["04", "Compare", "Pareto dominance across axes chosen per lens. A single composite score does not exist in the code."],
  ["05", "Refuse", "Eligibility filters run first; a gap ledger and a provenance graph travel with every result."],
];
const cw = (12.1 - 4 * 0.22) / 5;
steps.forEach((s, i) => {
  const x = M + i * (cw + 0.22);
  card(s3, x, 2.22, cw, 2.02);
  s3.addText(s[0], { x: x + 0.22, y: 2.34, w: cw - 0.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: ACC, margin: 0, isTextBox: true });
  s3.addText(s[1], { x: x + 0.22, y: 2.66, w: cw - 0.4, h: 0.32, fontFace: HEAD, fontSize: 15.5, bold: true, color: INK, margin: 0, isTextBox: true });
  s3.addText(s[2], { x: x + 0.22, y: 3.02, w: cw - 0.4, h: 1.1, fontFace: BODY, fontSize: 11, color: MUTE, lineSpacing: 14.5, margin: 0, isTextBox: true, valign: "top" });
});

panel(s3, "earth_strip.png", M, 4.52, 8.42, 1.86, "Input is real map data, not a synthetic stand-in — shown here at 30 m posting.", MUTE);
const bodies = ["Earth", "Mars", "Moon", "Mercury", "Ceres"];
bodies.forEach((b, i) => {
  const y = 4.62 + i * 0.36;
  s3.addShape(pres.ShapeType.roundRect, { x: 9.42, y, w: 3.3, h: 0.3, rectRadius: 0.05, fill: { color: PANEL }, line: { color: RULE, width: 1 } });
  s3.addText(b, { x: 9.62, y: y + 0.01, w: 2.9, h: 0.28, fontFace: BODY, fontSize: 12, color: INK, margin: 0, isTextBox: true, valign: "middle" });
});
s3.addText("Five bodies, one method.", { x: 9.42, y: 6.42, w: 3.3, h: 0.3, fontFace: BODY, fontSize: 11, color: WARM, margin: 0, isTextBox: true });

/* ======================================================== 4 · measurement == */
const s4 = pres.addSlide({ masterName: "MAIN", sectionTitle: "Method" });
kicker(s4, "The measurement layer");
s4.addText("Depth where it is cited, restraint where it is not", { placeholder: "title" });
lede(s4, "Every descriptor carries a definition, a unit, a window and a citation — and a stated claim boundary.", 1.62, 0.4, 12.1);

stat(s4, M, 2.22, 2.8, "40", "descriptor families, each cited to the literature it comes from", ACC);
stat(s4, M + 3.02, 2.22, 2.8, "~290", "scalar outputs emitted by the descriptor bank", ACC);
stat(s4, M + 6.04, 2.22, 2.8, "6", "decision lenses — five by default, hydro opt-in", ACC);
stat(s4, M + 9.06, 2.22, 3.04, "0", "composite scores anywhere in the codebase", WARM);

card(s4, M, 4.22, 5.95, 2.16);
s4.addText("Axes, not a verdict", { x: M + 0.28, y: 4.38, w: 5.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s4.addText([
  { text: "Slope, relief, ruggedness, connectivity, curvature, vector ruggedness, roughness/Hurst, openness, geomorphons, power spectrum, anisotropy.", options: { bullet: true, breakLine: true } },
  { text: "The decision is Pareto dominance over a small declared set per lens — so a candidate that wins on roughness cannot be quietly traded against one that wins on relief.", options: { bullet: true } },
], { x: M + 0.28, y: 4.74, w: 5.4, h: 1.5, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, paraSpaceAfter: 6 });

card(s4, 6.77, 4.22, 5.95, 2.16);
s4.addText("Five result states, three of them refusals", { x: 6.77 + 0.28, y: 4.38, w: 5.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s4.addText([
  { text: "RECOMMEND_FOLLOW_UP and TIE, plus INDETERMINATE (insufficient evidence) and NOT_COMPARABLE.", options: { bullet: true, breakLine: true } },
  { text: "BLOCKED is a real outcome: a water or flat tile is filtered out before it can be scored.", options: { bullet: true, breakLine: true } },
  { text: "Eligibility filtering runs BEFORE comparison: a blocked unit is never scored, and a study that cannot separate candidates is allowed to say so.", options: { bullet: true } },
], { x: 6.77 + 0.28, y: 4.74, w: 5.4, h: 1.5, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, paraSpaceAfter: 6 });

/* ========================================================= 5 · benchmark === */
const s5 = pres.addSlide({ masterName: "MAIN", sectionTitle: "Method" });
kicker(s5, "The benchmark, including the part that went against us");
s5.addText("We withdrew our own headline finding", { placeholder: "title" });
lede(s5, "Three acts, recorded in the order they happened: Act II is pre-registered, Act III is pre-specified.", 1.62, 0.34, 12.1);

const acts = [
  ["Act I · exploratory", "A real multi-region atlas suggested an analog we liked.", "Published 2026-10-11. Screened as a hypothesis — never as a result."],
  ["Act II · pre-registered", "A matched-footprint test to falsify it.", "Protocol frozen 2026-10-16 before any v2 result. It failed; the claim was withdrawn."],
  ["Act III · pre-specified", "Protocol v3 asked what actually explained the match.", "Rules and config predate the 2026-11-05 run. The protocol document does not."],
];
acts.forEach((a, i) => {
  const x = M + i * (3.98 + 0.22);
  card(s5, x, 2.18, 3.98, 2.14);
  s5.addText(a[0], { x: x + 0.28, y: 2.34, w: 3.44, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: i === 1 ? WARM : ACC, margin: 0, isTextBox: true });
  s5.addText(a[1], { x: x + 0.28, y: 2.7, w: 3.44, h: 0.7, fontFace: BODY, fontSize: 12.5, color: INK, lineSpacing: 16, margin: 0, isTextBox: true, valign: "top" });
  s5.addText(a[2], { x: x + 0.28, y: 3.44, w: 3.44, h: 0.7, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, valign: "top" });
});

card(s5, M, 4.62, 12.1, 1.6, "101826");
s5.addText("Protocol v3, confirmatory cells", { x: M + 0.3, y: 4.78, w: 4.0, h: 0.3, fontFace: HEAD, fontSize: 14, bold: true, color: INK, margin: 0, isTextBox: true });
s5.addText("15/15 honest cells · 0 comparability-gate violations · 11 unchanged · 1 destabilised · 3 membership-changed · 0 reversed", {
  x: M + 0.3, y: 5.1, w: 7.6, h: 0.4, fontFace: BODY, fontSize: 12.5, color: INK, margin: 0, isTextBox: true });
s5.addText("All six classes, none hidden: 11 unchanged, 1 destabilised, 3 membership-changed, and 0 stabilised, 0 reversed, 0 error. Pre-specified, not fully pre-registered: the rules and config predate the run; the protocol document does not.", {
  x: M + 0.3, y: 5.52, w: 7.6, h: 0.62, fontFace: BODY, fontSize: 11, color: WARM, lineSpacing: 14.5, margin: 0, isTextBox: true, valign: "top" });
s5.addText("15 / 15", { x: 10.05, y: 4.86, w: 2.4, h: 0.8, fontFace: HEAD, fontSize: 34, bold: true, color: ACC, margin: 0, isTextBox: true, align: "right" });

pres.addSection({ title: "Result" });
/* =========================================================== 6 · finding === */
const s6 = pres.addSlide({ masterName: "MAIN", sectionTitle: "Result" });
kicker(s6, "The result");
s6.addText("Within this panel and lens: roughness tracks the class, origin does not", { placeholder: "title" });

s6.addChart(pres.ChartType.bar, [{
  name: "σ (m)",
  labels: ["Nullarbor Plain (control)", "Llano Estacado (control)", "Deccan Traps", "Snake River Plain", "Harrat Khaybar", "Odadahraun", "Nevada Basin"],
  values: [5, 14, 32, 95, 102, 182, 562],
}], {
  x: M - 0.06, y: 1.86, w: 7.5, h: 4.4, barDir: "bar",
  chartColors: ["6FD6C0", "6FD6C0", "E0913F", "E0913F", "E0913F", "E0913F", "8C9AAD"],
  showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 11, dataLabelFontFace: "+mn-lt",
  showLegend: false, showTitle: false,
  catAxisLabelColor: MUTE, catAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt",
  valAxisLabelColor: MUTE, valAxisLabelFontSize: 10, valAxisLabelFontFace: "+mn-lt",
  valAxisLogScaleBase: 10, valAxisMinVal: 1, valAxisMaxVal: 1000,
  valGridLine: { color: RULE, size: 1 }, catGridLine: { style: "none" },
  chartArea: { fill: { color: BG } }, plotArea: { fill: { color: BG } },
});
s6.addText("σ = measured roughness of each Earth candidate at 60 km support (teal = smooth non-volcanic control, amber = basaltic, grey = neither; log scale). S = smoothness/shortlist, V = volcanic specificity, R = resolution robustness.", {
  x: M - 0.06, y: 6.32, w: 7.5, h: 0.42, fontFace: BODY, fontSize: 10.5, color: MUTE, lineSpacing: 13, margin: 0, isTextBox: true, valign: "top" });

card(s6, 8.5, 1.82, 4.22, 2.36);
s6.addText("S — SUPPORTED", { x: 8.78, y: 1.96, w: 3.7, h: 0.28, fontFace: BODY, fontSize: 12, bold: true, color: ACC, charSpacing: 1.0, margin: 0, isTextBox: true });
s6.addText("A smooth non-volcanic control holds Pareto layer 1 at every honest support, for all three volcanic-plains references.", {
  x: 8.78, y: 2.26, w: 3.7, h: 0.66, fontFace: BODY, fontSize: 11, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, valign: "top" });
s6.addText("V — NOT SUPPORTED", { x: 8.78, y: 3.02, w: 3.7, h: 0.28, fontFace: BODY, fontSize: 12, bold: true, color: WARM, charSpacing: 1.0, margin: 0, isTextBox: true });
s6.addText("It did not establish the pre-declared volcanic-specific advantage, over this panel and lens.", {
  x: 8.78, y: 3.32, w: 3.7, h: 0.72, fontFace: BODY, fontSize: 11, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, valign: "top" });

card(s6, 8.5, 4.34, 4.22, 2.44);
s6.addText("R — SUPPORTED", { x: 8.78, y: 4.48, w: 3.7, h: 0.28, fontFace: BODY, fontSize: 12, bold: true, color: ACC, charSpacing: 1.0, margin: 0, isTextBox: true });
s6.addText("Of 15 confirmatory cells: 11 unchanged, 1 destabilised, 3 membership-changed, 0 reversed. The destabilised cell is mars_solis at 1500 m.", {
  x: 8.78, y: 4.78, w: 3.7, h: 0.78, fontFace: BODY, fontSize: 11, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, valign: "top" });
s6.addText("Where it is soft", { x: 8.78, y: 5.64, w: 3.7, h: 0.28, fontFace: BODY, fontSize: 12, bold: true, color: WARM, charSpacing: 1.0, margin: 0, isTextBox: true });
s6.addText("The top pick is a near-tie; it reverses on a 6-px crop shift. The class result is robust, the ranking is not.", {
  x: 8.78, y: 5.94, w: 3.7, h: 0.74, fontFace: BODY, fontSize: 11, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, valign: "top" });

pres.addSection({ title: "Evidence" });
/* ====================================================== 7 · verification === */
const s7 = pres.addSlide({ masterName: "MAIN", sectionTitle: "Evidence" });
kicker(s7, "Evidence");
s7.addText("Claims are cheap; these are checked", { placeholder: "title" });
let BUILD_COMMIT = "uncommitted";
try { BUILD_COMMIT = require("child_process").execSync("git rev-parse --short HEAD", { cwd: __dirname }).toString().trim(); } catch (e) {}
s7.addText(`${BUILD_COMMIT} = the tested implementation commit; the deck is rebuilt after it · CI: github.com/pal-123456789/terratrace/actions`, {
  x: M, y: 6.48, w: 12.1, h: 0.32, fontFace: "Courier New", fontSize: 11, color: ACC, margin: 0, isTextBox: true });
lede(s7, "Every number below is produced by a command in the repository, and the documentation guard fails the build if the prose disagrees with the code.", 1.62, 0.42, 12.1);

stat(s7, M, 2.26, 3.7, "878", "offline tests — no network, no fixtures downloaded, run by a dependency-free runner", ACC);
stat(s7, M + 3.95, 2.26, 3.7, "51", "scientific-correctness oracles over analytic surfaces with known answers", ACC);
stat(s7, M + 7.9, 2.26, 4.2, "2", "independent runs that reproduce the canonical artifact hash", ACC);

card(s7, M, 3.9, 5.95, 2.48);
s7.addText("What the gates actually do", { x: M + 0.28, y: 4.06, w: 5.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s7.addText([
  { text: "A comparability gate refuses to display any value below the scale that supports it.", options: { bullet: true, breakLine: true } },
  { text: "A claim-firewall test fails the build if a forbidden claim appears in the output.", options: { bullet: true, breakLine: true } },
  { text: "A documentation-consistency guard recomputes every published count from source and names the file when prose drifts.", options: { bullet: true } },
], { x: M + 0.28, y: 4.42, w: 5.4, h: 1.82, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, paraSpaceAfter: 7 });

card(s7, 6.77, 3.9, 5.95, 2.48);
s7.addText("Continuous integration on three Pythons", { x: 6.77 + 0.28, y: 4.06, w: 5.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s7.addText([
  { text: "3.10, 3.11 and 3.12 with NumPy only — the suite, an optional-dependency hygiene check that runs every test mentioning an optional package, the 51 oracles, and the doc guard.", options: { bullet: true, breakLine: true } },
  { text: "An end-to-end job builds the study and the viewer and uploads the bundle. These are repeatable software outputs — they are NOT independent scientific replication.", options: { bullet: true } },
], { x: 6.77 + 0.28, y: 4.42, w: 5.4, h: 1.82, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, paraSpaceAfter: 7 });

/* ============================================================= 8 · data ===== */
const s8 = pres.addSlide({ masterName: "MAIN", sectionTitle: "Evidence" });
kicker(s8, "Data and provenance");
s8.addText("A keyless path to real 30 m Earth data", { placeholder: "title" });
lede(s8, "The benchmark runs with no credentials at all.", 1.62, 0.34, 8.2);

card(s8, M, 2.2, 8.2, 1.86);
s8.addText("Copernicus GLO-30 on AWS Open Data", { x: M + 0.28, y: 2.36, w: 7.6, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s8.addText("Proven bit-identical to the OpenTopography COP30 product — maximum absolute difference 0.00 m, 100 % of pixels identical. The API key is now optional, not required.", {
  x: M + 0.28, y: 2.7, w: 7.6, h: 0.62, fontFace: BODY, fontSize: 12, color: MUTE, lineSpacing: 16, margin: 0, isTextBox: true, valign: "top" });
s8.addText("One command, no credential.", { x: M + 0.28, y: 3.42, w: 7.6, h: 0.5, fontFace: "Courier New", fontSize: 11.5, color: ACC, margin: 0, isTextBox: true, valign: "top" });

card(s8, M, 4.24, 8.2, 2.14);
s8.addText([
  { text: "15 catalogued products, each with coverage geometry, licence and terms, vertical accuracy and nodata policy — and a per-file SHA-256 in a source lock.", options: { bullet: true, breakLine: true } },
  { text: "An evidence graph records every source, transform and unit behind every visible number.", options: { bullet: true, breakLine: true } },
  { text: "The whole canonical flow runs offline; no live dependency sits in the demo path.", options: { bullet: true } },
], { x: M + 0.28, y: 4.4, w: 7.6, h: 1.86, fontFace: BODY, fontSize: 12, color: MUTE, lineSpacing: 16, margin: 0, isTextBox: true, paraSpaceAfter: 7 });

panel(s8, "mars_panel.png", 9.42, 2.2, 3.3, 2.05, "Mars reference terrain · MOLA, 463 m/px nominal", WARM);
card(s8, 9.42, 4.66, 3.3, 1.72, "101826");
s8.addText("Independent toolchain check", { x: 9.66, y: 4.78, w: 2.9, h: 0.28, fontFace: HEAD, fontSize: 12.5, bold: true, color: INK, margin: 0, isTextBox: true });
s8.addText("3x3 relief: within 0.0001 m\nSlope means: within 0.016 deg\nReprojection: vs closed-form geodesy, within 0.00003 m\nCell-size and window-anchor assumptions:\ndocumented differences\nExternal reviewer: none yet", { x: 9.66, y: 5.08, w: 2.9, h: 1.22, fontFace: BODY, fontSize: 9.5, color: MUTE, lineSpacing: 12, margin: 0, isTextBox: true, valign: "top" });
s8.addText("Five bodies, each reprojected onto its own metric grid and compared at a common effective support, never at nominal posting.", { x: 9.42, y: 6.46, w: 3.3, h: 0.46, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, valign: "top" });

/* ========================================================== 9 · firewall === */
const s9 = pres.addSlide({ masterName: "MAIN", sectionTitle: "Evidence" });
kicker(s9, "What it refuses to claim, and what is not finished");
s9.addText("The firewall is the feature", { placeholder: "title" });

card(s9, M, 1.86, 6.1, 2.5, "1A0F08");
s9.addText("Never claimed, by design", { x: M + 0.3, y: 2.02, w: 5.5, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: WARM, margin: 0, isTextBox: true });
s9.addText([
  { text: "Rover traversability, autonomy or mission readiness.", options: { bullet: true, breakLine: true } },
  { text: "Geological equivalence between two bodies.", options: { bullet: true, breakLine: true } },
  { text: "Site access, permitting, ecology or community impact.", options: { bullet: true, breakLine: true } },
  { text: "Any single “Mars-likeness” score.", options: { bullet: true } },
], { x: M + 0.3, y: 2.4, w: 5.5, h: 1.8, fontFace: BODY, fontSize: 12.5, color: INK, lineSpacing: 17, margin: 0, isTextBox: true, paraSpaceAfter: 8 });
s9.addText("This is an analog-screening instrument. It narrows a search; it does not certify a site.", {
  x: M + 0.3, y: 3.9, w: 5.5, h: 0.36, fontFace: BODY, fontSize: 11.5, italic: true, color: MUTE, margin: 0, isTextBox: true });

card(s9, 7.02, 1.86, 5.7, 2.5);
s9.addText("Open, and named rather than hidden", { x: 7.02 + 0.3, y: 2.02, w: 5.1, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
// Four bullets, each held to roughly two lines at this width: a five-bullet version overran the
// card and printed its caption across the last bullet. Text frames with valign "top" do not
// shrink to fit — the overflow is silent in the generator and only visible when the slide is
// rendered, which is why the deck is rasterised and read before it is shipped.
s9.addText([
  { text: "Two descriptors re-derived independently; no external reviewer yet.", options: { bullet: true, breakLine: true } },
  { text: "No demo video; the script for it ships in the repository.", options: { bullet: true, breakLine: true } },
  { text: "All six lunar sites screened and the answer survives the DEM error ensemble — but it is exploratory, and the roughest sites have no close match.", options: { bullet: true, breakLine: true } },
  { text: "No external user walkthrough yet; the boundary is argued, not tested.", options: { bullet: true } },
], { x: 7.02 + 0.3, y: 2.34, w: 5.1, h: 1.5, fontFace: BODY, fontSize: 11, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, paraSpaceAfter: 7 });
// 3.98, not 3.9: the bullet block above ends near 3.8" and a caption inside that footprint is
// printed straight through the last bullet. The card runs to 4.36", so there is room below it.
s9.addText("Every open item is listed first in the traceability page, not buried.", {
  x: 7.02 + 0.3, y: 3.98, w: 5.1, h: 0.34, fontFace: BODY, fontSize: 11.5, italic: true, color: ACC, margin: 0, isTextBox: true });

card(s9, M, 4.6, 12.1, 1.72);
s9.addText("Why this matters for the challenge", { x: M + 0.3, y: 4.76, w: 11.5, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s9.addText("A shortlist is only useful if the person reading it can see exactly how far the evidence goes. A tool that will not say “this is a safe place to land” is more trustworthy for saying so than one that quietly implies it.", {
  x: M + 0.3, y: 5.12, w: 11.5, h: 0.9, fontFace: BODY, fontSize: 12.5, color: MUTE, lineSpacing: 17, margin: 0, isTextBox: true, valign: "top" });

pres.addSection({ title: "Find it" });
/* ============================================================= 10 · find ==== */
const s10 = pres.addSlide({ masterName: "MAIN", sectionTitle: "Find it" });
kicker(s10, "Where to find it");
s10.addText("Everything is public, offline, and reproducible", { placeholder: "title" });

card(s10, M, 1.86, 7.4, 2.28);
s10.addText("Reproduce the headline result", { x: M + 0.3, y: 2.02, w: 6.9, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s10.addText("pip install numpy rasterio\npython -m terratrace.cli study --config config/matched_footprint_v3.yml --source cog", {
  x: M + 0.3, y: 2.4, w: 6.9, h: 0.9, fontFace: "Courier New", fontSize: 11, color: ACC, lineSpacing: 16, margin: 0, isTextBox: true, valign: "top" });
s10.addText("Offline once the tiles are cached: the viewer, the reports and the study package need no network. Fetching the DEMs for the first time does.", {
  x: M + 0.3, y: 3.42, w: 6.9, h: 0.6, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, valign: "top" });

card(s10, 8.42, 1.86, 4.3, 2.28);
s10.addText("Read it", { x: 8.72, y: 2.02, w: 3.8, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s10.addText([
  { text: "The site, the v3 results page, the generated study viewer.", options: { bullet: true, breakLine: true } },
  { text: "The paper, validation report and limitations.", options: { bullet: true, breakLine: true } },
  { text: "The traceability page against the project's own master plan.", options: { bullet: true, breakLine: true } },
  { text: "The exploratory lunar demonstration on real LOLA terrain.", options: { bullet: true } },
], { x: 8.72, y: 2.4, w: 3.8, h: 1.62, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, paraSpaceAfter: 7 });

card(s10, M, 4.34, 12.1, 1.98);
s10.addImage({ path: require("path").join(REPO_ROOT, "assets", "qr_repo.png"), x: 12.05, y: 1.92, w: 1.05, h: 1.05 });
s10.addText("Repository", { x: 11.62, y: 3.02, w: 1.9, h: 0.24, fontFace: BODY, fontSize: 9.5, color: MUTE, align: "center", margin: 0, isTextBox: true });
s10.addText("The honest ask", { x: M + 0.3, y: 4.5, w: 5.0, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s10.addText("The engine is prior art, built weeks ahead of the event. What a team adds from here is the part that counts: a second terrain family it has never seen, an independent re-derivation of one window by a different GIS toolchain, or a validation set drawn by someone with planetary field experience. If you would rather find the place where this quietly overclaims than add a feature, that is the most useful thing you could do to it.", {
  x: M + 0.3, y: 4.86, w: 11.5, h: 1.3, fontFace: BODY, fontSize: 12.5, color: MUTE, lineSpacing: 17, margin: 0, isTextBox: true, valign: "top" });

pres.writeFile({ fileName: OUT }).then(async () => {
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
});
