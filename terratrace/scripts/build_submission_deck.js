/* TerraTrace SUBMISSION deck — 7 slides, for the official submission form.
 *
 * This is deliberately NOT the 10-slide technical deck (`build_deck.js`). That one walks the whole
 * project: the method, the ablation, the verification evidence, the open items. This one is what a
 * judge reads in two minutes and has to be able to act on: what the thing is, what it found, what it
 * refuses to claim, and where to find it.
 *
 * The palette is a COPY of the technical deck's, not an import — extracting a shared module would
 * mean editing the file that currently builds a verified deck, and the risk is not worth the
 * tidiness here. Because a copied constant is exactly the thing that silently drifts, the two files'
 * palettes are asserted equal in `tests/test_deck_palette.py`. Add a colour to one and the test
 * tells you to add it to the other.
 */
const pptxgen = require("pptxgenjs");

const REPO_ROOT = require("path").resolve(__dirname, "..", "..");
const ASSETS = process.env.DECK_ASSETS || require("path").join(REPO_ROOT, "assets", "deck");
const OUT = require("path").join(REPO_ROOT, "TerraTrace-submission.pptx");

function loadApplyTheme() {
  const candidates = [
    process.env.PPTX_APPLY_THEME,
    require("path").join(__dirname, "apply_theme.js"),
    process.env.PPTX_SKILLS_DIR
      ? require("path").join(process.env.PPTX_SKILLS_DIR, "pptx", "scripts", "apply_theme.js")
      : null,
  ].filter(Boolean);
  for (const c of candidates) {
    try { return require(c).applyTheme; } catch (e) { /* try the next */ }
  }
  return null;
}
const applyTheme = loadApplyTheme();

const THEME = {
  name: "TerraTrace Dark",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "EEF2F7", lt1: "05070C", dk2: "6FD6C0", lt2: "0B1220",
    accent1: "6FD6C0", accent2: "E0913F", accent3: "2D4A55", accent4: "8C9AAD",
    accent5: "A9C9C6", accent6: "1D2634", hlink: "6FD6C0", folHlink: "8C9AAD",
  },
};

const INK = "EEF2F7", MUTE = "8C9AAD", ACC = "6FD6C0", WARM = "E0913F",
      RULE = "1D2634", PANEL = "0B1220", BG = "05070C";
const HEAD = "Cambria", BODY = "Calibri";
const M = 0.62, W = 13.33, H = 7.5;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Pal Ghevariya";
pres.title = "TerraTrace — submission";
pres.subject = "Earth terrains that analog the Moon and Mars, at a declared common support";

function titlePlaceholder(size) {
  return [{ placeholder: { options: {
    name: "title", type: "title", x: M, y: 0.66, w: 12.1, h: 0.86,
    fontFace: HEAD, fontSize: size, bold: true, color: INK, align: "left", valign: "middle", margin: 0,
  }, text: "" } }];
}
function chrome() {
  return [{ text: { text: "TerraTrace  ·  terratrace.fit", options: {
    x: M, y: 6.98, w: 6.0, h: 0.3, fontFace: BODY, fontSize: 10, color: MUTE, margin: 0, isTextBox: true } } }];
}

pres.defineSlideMaster({ title: "COVER", background: { color: BG }, objects: [] });
pres.defineSlideMaster({
  title: "MAIN", background: { color: BG },
  objects: [...titlePlaceholder(30), ...chrome()],
  slideNumber: { x: 12.35, y: 6.98, w: 0.6, h: 0.3, color: MUTE, fontFace: BODY, fontSize: 10, align: "right" },
});

function kicker(slide, text) {
  slide.addText(text.toUpperCase(), {
    x: M, y: 0.38, w: 11.0, h: 0.26, fontFace: BODY, fontSize: 11, bold: true,
    color: ACC, charSpacing: 1.4, margin: 0, isTextBox: true });
}
function inlineRuns(text, boldColor) {
  if (!text.includes("**")) return text;
  const runs = [];
  text.split("**").forEach((part, i) => {
    if (!part) return;
    runs.push(i % 2 === 1 ? { text: part, options: { bold: true, color: boldColor || INK } }
                          : { text: part, options: {} });
  });
  return runs.length ? runs : text;
}
function lede(slide, text, y, h, w) {
  slide.addText(inlineRuns(text), {
    x: M, y, w: w || 12.1, h, fontFace: BODY, fontSize: 15, color: MUTE,
    lineSpacing: 22, margin: 0, isTextBox: true, valign: "top" });
}
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06, fill: { color: fill || PANEL },
    line: { color: RULE, width: 1 },
    shadow: { type: "outer", color: "000000", blur: 12, offset: 3, angle: 90, opacity: 0.35 } });
}
function stat(slide, x, y, w, big, label, color) {
  card(slide, x, y, w, 1.5);
  slide.addText(big, { x: x + 0.24, y: y + 0.16, w: w - 0.48, h: 0.62, fontFace: HEAD,
    fontSize: 30, bold: true, color: color || ACC, margin: 0, isTextBox: true });
  slide.addText(label, { x: x + 0.24, y: y + 0.8, w: w - 0.48, h: 0.58, fontFace: BODY,
    fontSize: 10.5, color: MUTE, lineSpacing: 13, margin: 0, isTextBox: true, valign: "top" });
}

/* ============================================================= 1 · title ==== */
// `assets/cover.png` is a finished POSTER — it already contains the title, the subtitle and the
// verdicts. Using it as the slide background while also writing a title on top printed the words
// twice, which is what an earlier revision of this slide did. The slide is therefore built from
// plain elements plus two terrain panels, and the poster is left to the README and the landing page.
const s1 = pres.addSlide({ masterName: "COVER" });
s1.addText("TerraTrace", { x: M, y: 0.7, w: 8.2, h: 0.92, fontFace: HEAD, fontSize: 46,
  bold: true, color: INK, margin: 0, isTextBox: true });
s1.addText("Earth terrains that answer to the Moon and Mars", { x: M, y: 1.56, w: 8.2, h: 0.44,
  fontFace: HEAD, fontSize: 20, color: ACC, margin: 0, isTextBox: true });
s1.addText("Submitted to the NASA Space Apps Challenge 2026 challenge “Identify Earth Locations that\nAnalog the Permanent Moon Base Locations and Mars”. Published as open prior art, built and\ngated weeks before the event — stated openly rather than dressed up as event work.", {
  x: M, y: 2.12, w: 7.9, h: 1.2, fontFace: BODY, fontSize: 12, color: MUTE,
  lineSpacing: 16.5, margin: 0, isTextBox: true, valign: "top" });
s1.addText("terratrace.fit", { x: M, y: 3.42, w: 5.0, h: 0.36, fontFace: "Courier New",
  fontSize: 16, bold: true, color: ACC, margin: 0, isTextBox: true });
s1.addText("github.com/pal-123456789/terratrace", { x: M, y: 3.84, w: 6.0, h: 0.32,
  fontFace: "Courier New", fontSize: 12, color: MUTE, margin: 0, isTextBox: true });

// one terrain panel for texture, at its true aspect ratio and un-stretched, as everywhere else
s1.addImage({ path: require("path").join(ASSETS, "khaybar.png"), x: 9.35, y: 0.95, w: 3.35, h: 3.35 });
s1.addText("Harrat Khaybar, Saudi Arabia · real Copernicus GLO-30 terrain", {
  x: 9.35, y: 4.36, w: 3.35, h: 0.3, fontFace: BODY, fontSize: 8.5, color: MUTE,
  margin: 0, isTextBox: true });

s1.addText("Seven Earth candidates, one light direction and one vertical scale across every panel — nothing contrast-stretched, so flat terrain reads as flat.", {
  x: M, y: 4.6, w: 12.1, h: 0.28, fontFace: BODY, fontSize: 9.5, color: MUTE, margin: 0, isTextBox: true });
s1.addImage({ path: require("path").join(ASSETS, "earth_strip.png"), x: M, y: 4.94, w: 12.09, h: 2.5 });

/* ========================================================= 2 · the question == */
const s2 = pres.addSlide({ masterName: "MAIN" });
kicker(s2, "The question");
s2.addText("Which Earth terrains are morphologically comparable — and at what scale?", { placeholder: "title" });
lede(s2, "One narrow, measurable question. TerraTrace answers it with **measured distance between real elevation models**, and with the scale at which the comparison is honest. It does not answer “where should we land”, and it says so everywhere it could be misread.", 1.66, 1.0);

card(s2, M, 2.86, 5.95, 1.66);
s2.addText("What it does", { x: M + 0.28, y: 3.0, w: 5.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s2.addText([
  { text: "Reprojects every terrain onto its own body's metric grid.", options: { bullet: true, breakLine: true } },
  { text: "Aggregates to a common support, so no unit is compared below its source resolution.", options: { bullet: true, breakLine: true } },
  { text: "Ranks by Pareto dominance over declared axes — never a composite score.", options: { bullet: true } },
], { x: M + 0.28, y: 3.34, w: 5.4, h: 1.1, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, paraSpaceAfter: 5 });

card(s2, 6.77, 2.86, 5.95, 1.66);
s2.addText("What it refuses", { x: 6.77 + 0.28, y: 3.0, w: 5.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: WARM, margin: 0, isTextBox: true });
s2.addText([
  { text: "Traversability, autonomy, mission readiness.", options: { bullet: true, breakLine: true } },
  { text: "Geological equivalence between two bodies.", options: { bullet: true, breakLine: true } },
  { text: "Site access, permitting or ecology.", options: { bullet: true, breakLine: true } },
  { text: "Any single “Mars-likeness” score.", options: { bullet: true } },
], { x: 6.77 + 0.28, y: 3.34, w: 5.4, h: 1.1, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, paraSpaceAfter: 5 });

card(s2, M, 4.68, 12.1, 1.16);
s2.addText("Five result states, three of them refusals — including BLOCKED, when a unit cannot be compared at all. A tool that will not say “this is a safe place to land” is more trustworthy for saying so.", {
  x: M + 0.28, y: 4.86, w: 11.5, h: 0.8, fontFace: BODY, fontSize: 12.5, color: MUTE, lineSpacing: 17, margin: 0, isTextBox: true, valign: "top" });

/* ============================================================ 3 · the method == */
const s3 = pres.addSlide({ masterName: "MAIN" });
kicker(s3, "What it is built on");
s3.addText("Five worlds, one method, no black box", { placeholder: "title" });

stat(s3, M, 1.9, 2.8, "5", "planetary bodies: Earth, Mars, the Moon, Mercury, Ceres", ACC);
stat(s3, M + 3.02, 1.9, 2.8, "40", "cited descriptor families (~290 scalar values)", ACC);
stat(s3, M + 6.04, 1.9, 2.8, "884", "offline tests, 0 network required to run them", ACC);
stat(s3, M + 9.06, 1.9, 3.04, "51", "scientific-correctness oracles over the operators", ACC);

card(s3, M, 3.66, 5.95, 2.18);
s3.addText("Real data, keyless", { x: M + 0.28, y: 3.8, w: 5.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s3.addText([
  { text: "Mars MOLA · Moon LOLA · Mercury MESSENGER · Ceres Dawn.", options: { bullet: true, breakLine: true } },
  { text: "Earth: ESA Copernicus GLO-30, read straight from the public AWS COG mosaic — no account, no key.", options: { bullet: true, breakLine: true } },
  { text: "15 catalogued products, each with coverage, licence, vertical accuracy and a per-file SHA-256.", options: { bullet: true } },
], { x: M + 0.28, y: 4.14, w: 5.4, h: 1.6, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, paraSpaceAfter: 5 });

card(s3, 6.77, 3.66, 5.95, 2.18);
s3.addText("Depth where it is cited, restraint where it is not", { x: 6.77 + 0.28, y: 3.8, w: 5.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s3.addText([
  { text: "Slope, relief, ruggedness, connectivity, curvature, roughness/Hurst, openness, geomorphons, anisotropy.", options: { bullet: true, breakLine: true } },
  { text: "Every descriptor carries a definition, a unit, a window and a citation — and a stated claim boundary.", options: { bullet: true, breakLine: true } },
  { text: "A mechanical guard fails the build if any published number stops matching the code.", options: { bullet: true } },
], { x: 6.77 + 0.28, y: 4.14, w: 5.4, h: 1.6, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, paraSpaceAfter: 5 });

/* ============================================================ 4 · the Mars result */
const s4 = pres.addSlide({ masterName: "MAIN" });
kicker(s4, "Result 1 · Mars · protocol v3");
s4.addText("It caught its own false analog", { placeholder: "title" });
lede(s4, "An earlier exploratory run favoured “Craters of the Moon, Idaho” — a famous basalt analog. We tested that under a protocol frozen before the data, and **withdrew it ourselves**.", 1.6, 0.68);

const v3 = [
  ["S", "SUPPORTED", "smoothness tracks the class", ACC],
  ["V", "NOT SUPPORTED", "volcanic origin adds nothing", WARM],
  ["R", "SUPPORTED", "no candidate reversal under resolution matching", ACC],
];
v3.forEach(([letter, verdict, why, col], i) => {
  const y = 2.4 + i * 0.72;
  card(s4, M, y, 8.4, 0.64);
  s4.addText(letter, { x: M + 0.22, y: y + 0.1, w: 0.4, h: 0.44, fontFace: HEAD, fontSize: 20, bold: true, color: col, margin: 0, isTextBox: true });
  s4.addText(verdict, { x: M + 0.72, y: y + 0.17, w: 2.3, h: 0.3, fontFace: BODY, fontSize: 12, bold: true, color: col, margin: 0, isTextBox: true });
  s4.addText(why, { x: M + 3.1, y: y + 0.18, w: 5.1, h: 0.3, fontFace: BODY, fontSize: 11.5, color: MUTE, margin: 0, isTextBox: true });
});
s4.addText("15 / 15 confirmatory cells accounted for. Every resolution-change class is reported, including the two that are zero: 11 unchanged, 0 stabilised, 1 destabilised, 0 reversed, 3 membership changed, 0 error.", {
  x: M, y: 4.66, w: 8.4, h: 0.7, fontFace: BODY, fontSize: 11, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, valign: "top" });
card(s4, 9.42, 2.4, 3.3, 2.96);
s4.addText("Read it honestly", { x: 9.7, y: 2.56, w: 2.8, h: 0.3, fontFace: HEAD, fontSize: 14, bold: true, color: INK, margin: 0, isTextBox: true });
s4.addText("v3 is pre-specified but not fully pre-registered — the rules and config were frozen before the data, the protocol document was committed after the run. We say so on every surface rather than letting a reader discover it.", {
  x: 9.7, y: 2.9, w: 2.8, h: 2.3, fontFace: BODY, fontSize: 10, color: MUTE, lineSpacing: 13, margin: 0, isTextBox: true, valign: "top" });
s4.addText("Within this panel and lens: roughness tracks the class, origin does not.", {
  x: M, y: 5.5, w: 12.1, h: 0.4, fontFace: BODY, fontSize: 12, italic: true, color: ACC, margin: 0, isTextBox: true });

/* ============================================================ 5 · the lunar half */
const s5 = pres.addSlide({ masterName: "MAIN" });
kicker(s5, "Result 2 · the Moon · real LOLA terrain · exploratory");
s5.addText("The other half of the challenge, run on real lunar data", { placeholder: "title" });
lede(s5, "All **six** published south-polar candidate regions from the NASA Goddard 5 m/pixel LOLA products, screened against the same Earth roster at a declared 500–1000 m support.", 1.6, 0.68);

const lunarStats = [
  ["18 / 18", "site × support cells where the same single Earth candidate is non-dominated"],
  ["6 / 6", "published error realisations in which that membership survives"],
  ["2 of 6", "sites with no candidate within 50% on every axis — screened, not matched"],
];
lunarStats.forEach(([big, label], i) => stat(s5, M + i * 4.13, 2.42, 3.7, big, label, i === 2 ? WARM : ACC));

card(s5, M, 4.14, 12.1, 1.7);
s5.addText("The honest shape of it", { x: M + 0.28, y: 4.28, w: 11.5, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s5.addText("Ordering is decisive everywhere; closeness almost nowhere. For Shackleton rim and Malapert massif the surviving candidate is 44–71% away on some axis — the least-dissimilar member of a weak shortlist, which is the exact failure mode we withdrew a Mars claim over. Naming that is the point. Mars itself is excluded from this regime by arithmetic, not convenience: MOLA's effective floor is above every support a 16 km tile can carry.", {
  x: M + 0.28, y: 4.6, w: 11.5, h: 1.1, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, valign: "top" });

/* ============================================================ 6 · the evidence */
const s6 = pres.addSlide({ masterName: "MAIN" });
kicker(s6, "Evidence & reproducibility");
s6.addText("Every number has a receipt", { placeholder: "title" });

stat(s6, M, 1.9, 2.8, "884", "offline tests across 95 modules, 0 failures", ACC);
stat(s6, M + 3.02, 1.9, 2.8, "51", "scientific-correctness oracles, stable hash", ACC);
stat(s6, M + 6.04, 1.9, 2.8, "4", "frozen artifact hashes, re-asserted after every change", ACC);
stat(s6, M + 9.06, 1.9, 3.04, "0", "credentials needed for the headline Earth data path", WARM);

card(s6, M, 3.66, 7.4, 2.2);
s6.addText("Reproduce the headline result", { x: M + 0.28, y: 3.8, w: 6.9, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s6.addText("pip install numpy rasterio\npython -m terratrace.cli study \\\n    --config config/matched_footprint_v3.yml --source cog", {
  x: M + 0.28, y: 4.14, w: 6.9, h: 1.0, fontFace: "Courier New", fontSize: 10.5, color: ACC,
  lineSpacing: 15, margin: 0, isTextBox: true, valign: "top" });
s6.addText("Offline once the tiles are cached. The engine re-derives two descriptors through an independent GIS toolchain, and validates its reprojection against closed-form geodesy rather than against a second wrapper around the same library.", {
  x: M + 0.28, y: 5.14, w: 6.9, h: 0.6, fontFace: BODY, fontSize: 10.5, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, valign: "top" });

card(s6, 8.14, 3.66, 4.58, 2.2);
s6.addText("What keeps it honest", { x: 8.42, y: 3.8, w: 4.1, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s6.addText([
  { text: "A guard computes every published count from the source and fails the build if prose drifts.", options: { bullet: true, breakLine: true } },
  { text: "A frozen claim ledger maps each claim to the evidence that would falsify it.", options: { bullet: true, breakLine: true } },
  { text: "The site's links, fragments and markup are checked before deployment.", options: { bullet: true } },
], { x: 8.42, y: 4.14, w: 4.1, h: 1.6, fontFace: BODY, fontSize: 10.5, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, paraSpaceAfter: 5 });

s6.addImage({ path: require("path").join(REPO_ROOT, "assets", "qr_repo.png"), x: 11.95, y: 5.98, w: 1.05, h: 1.05 });
s6.addText("Repository", { x: 11.5, y: 5.72, w: 1.9, h: 0.24, fontFace: BODY, fontSize: 9.5, color: MUTE, align: "center", margin: 0, isTextBox: true });

/* ============================================================ 7 · the limits */
const s7 = pres.addSlide({ masterName: "MAIN" });
kicker(s7, "Limits, and what would help most");
s7.addText("Named first, not buried", { placeholder: "title" });

card(s7, M, 1.86, 5.95, 2.9);
s7.addText("Open, and stated plainly", { x: M + 0.28, y: 2.0, w: 5.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: WARM, margin: 0, isTextBox: true });
s7.addText([
  { text: "The lunar work is exploratory: six nearby sites are not six independent tests.", options: { bullet: true, breakLine: true } },
  { text: "The error-ensemble check uses 6 of the 100 published realisations.", options: { bullet: true, breakLine: true } },
  { text: "No external reviewer has examined the independent reproduction.", options: { bullet: true, breakLine: true } },
  { text: "No demo video; the shot-by-shot script is in the repository.", options: { bullet: true } },
], { x: M + 0.28, y: 2.34, w: 5.4, h: 2.2, fontFace: BODY, fontSize: 11, color: MUTE, lineSpacing: 14, margin: 0, isTextBox: true, paraSpaceAfter: 6 });

card(s7, 6.77, 1.86, 5.95, 2.9);
s7.addText("The honest ask", { x: 6.77 + 0.28, y: 2.0, w: 5.4, h: 0.3, fontFace: HEAD, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
s7.addText("The engine is prior art, built weeks before the event. What a team adds from here is the part that counts: a second terrain family it has never seen, an independent re-derivation by a different GIS toolchain, or a validation set drawn by someone with planetary field experience. If you would rather find the place where this quietly overclaims than add a feature, that is the most useful thing you could do to it.", {
  x: 6.77 + 0.28, y: 2.34, w: 5.4, h: 2.3, fontFace: BODY, fontSize: 11.5, color: MUTE, lineSpacing: 15.5, margin: 0, isTextBox: true, valign: "top" });

card(s7, M, 4.92, 12.1, 1.3);
s7.addText("terratrace.fit", { x: M + 0.28, y: 5.06, w: 4.0, h: 0.36, fontFace: "Courier New", fontSize: 16, bold: true, color: ACC, margin: 0, isTextBox: true });
s7.addText("github.com/pal-123456789/terratrace", { x: M + 0.28, y: 5.46, w: 6.0, h: 0.34, fontFace: "Courier New", fontSize: 13, color: MUTE, margin: 0, isTextBox: true });
s7.addText("Method write-up, frozen protocols, claim ledger,\nvalidation report and limitations — all public.", {
  x: 6.4, y: 5.06, w: 6.0, h: 0.8, fontFace: BODY, fontSize: 11, color: MUTE, lineSpacing: 15, margin: 0, isTextBox: true, valign: "top" });

pres.writeFile({ fileName: OUT }).then(async () => {
  // applyTheme rewrites the package's master/theme parts so PowerPoint's Design panel shows this
  // palette. Optional: the slides carry their colours explicitly, so it is cosmetic.
  if (applyTheme) await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
});
