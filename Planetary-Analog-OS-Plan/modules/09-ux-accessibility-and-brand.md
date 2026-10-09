# 09 — UX, Accessibility, and Brand

## Design premise

The memorable element is not a neon globe. It is the **refusal-to-overclaim moment**: a candidate appears visually compelling, then the evidence panel says exactly which assumptions fail and what must be measured next.

## Visual language

### Palette

| Token | Hex | Meaning |
|---|---|---|
| Void ink | `#0A1118` | Deep-space text/background anchor |
| Regolith field | `#E7E1D5` | Warm mineral surface for docs/print |
| Mars oxide | `#A8513A` | Planetary reference accent; never “danger” alone |
| Signal cyan | `#38B5C5` | Evidence links and active comparison |
| Basalt slate | `#58636B` | Secondary data and uncertainty |
| Permission amber | `#D6A33A` | Unknown/review-needed status |
| Verified green | `#4C8B69` | Verified/eligible; paired with text/icon |
| Blocked plum | `#7B4056` | Rights/quality blocker; paired with text/icon |

Use a restrained mineral/signal palette. Avoid generic SaaS gradients and avoid making every surface a card.

### Typography

- Display: a distinctive high-contrast serif or humanist display face for the category statement only.
- Body: a highly legible sans with strong numerals for data tables.
- Data: tabular numerals, not a decorative monospace label system everywhere.
- Sentence case. Labels describe user decisions, not internal architecture.

### Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ TerraTrace  |  Map-scale morphology study  |  Evidence R4  │
├──────────────────────────────────────────────────────────────┤
│ What are you trying to compare?                              │
│ [Mars unit] [physical windows] [claim boundary]              │
├──────────────────────────────┬───────────────────────────────┤
│ Comparison table              │ Why this result?              │
│ unit | slope | relief | ...  │ source → transform → result   │
│                              │ what transfers / cannot       │
├──────────────────────────────┴───────────────────────────────┤
│ Sensitivity: stable / sensitive / tie / blocked              │
├──────────────────────────────────────────────────────────────┤
│ Draft study protocol + download evidence package             │
└──────────────────────────────────────────────────────────────┘
```

The table and evidence explanation are primary. The map is contextual, not the sole source of meaning.

## Information hierarchy

1. What question is being answered?
2. What is measured?
3. What is the evidence status?
4. What is the result state?
5. What does not transfer?
6. What must happen next?
7. How can a reviewer reproduce it?

## Interaction rules

- No score without a decomposition drawer.
- No green state without a text explanation.
- No “recommended” language if sensitivity returns a tie/indeterminate state.
- No hidden unit conversion.
- No map hover as the only evidence path.
- Every filter updates a visible “study configuration” line.
- URL state must reproduce the prepared study.
- Export action names the output: `Download study package`, not `Export data`.

## Accessibility acceptance

| Area | Requirement |
|---|---|
| Keyboard | Complete canonical journey without pointer |
| Screen reader | Semantic headings, table labels, chart summaries, focus management |
| Color | Text/icon/pattern redundancy; contrast checked |
| Motion | Reduced-motion variant; no information depends on animation |
| Zoom | 200% without loss of primary task |
| Mobile | 390 px primary flow; table/card fallback |
| Data | CSV/JSON/plain-text summaries |
| Language | Plain explanation plus scientific detail |
| Errors | Explain cause, effect, and next action |

## Empty and failure states

### No comparable units

> “No Earth unit can be compared at the selected support. This is a valid scientific result. Inspect product resolution, coverage, and common-support options.”

### Tie

> “The available evidence does not distinguish these units. Do not force a winner. The next useful study is shown below.”

### Blocked rights/access

> “Remote-sensing evidence exists, but publication or field-access status is not verified. This unit cannot be presented as an approved study site.”

### Offline

> “Live sources are unavailable. You are viewing the pinned release artifact from [manifest ID].”

## Demo choreography

The first minute must expose the category:

```text
question → observable → comparison → gap → next experiment
```

The app should not begin on a giant world map. It begins on a declared study question.

## Future internationalization

- UTC + local time where time appears.
- ISO dates.
- SI units with user-display preferences.
- Translation-ready string IDs.
- Local legal/governance fields, not US-centric hardcoding.
- Source-language evidence retained alongside translation.

## Design review checklist

- Could this interface be mistaken for a generic geospatial dashboard?
- Does the first view tell the user what the result can prove?
- Can a nonexpert locate the limitation without opening a documentation page?
- Does a visually attractive site unfairly dominate?
- Does the UI reward false certainty?
- Can a keyboard user reach the same scientific conclusion?
- Is the most important visual the evidence chain, not decoration?
