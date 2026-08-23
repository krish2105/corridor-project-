# Setup Runbook
### From nothing to Session 1, on the MacBook M4 Pro

---

# STEP 0 — Install tools

Open Terminal. Skip anything you already have.

```bash
# Homebrew (skip if `brew --version` works)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Follow the "Next steps" it prints — you must add brew to PATH on Apple Silicon:
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# Tools
brew install uv unar git

# Verify
uv --version && unar -v && git --version && claude --version
```

If `claude` isn't found, install Claude Code:
```bash
npm install -g @anthropic-ai/claude-code
```

---

# STEP 1 — Create the repo

```bash
mkdir -p ~/Desktop/corridor/{docs,src,tests,out}
mkdir -p ~/Desktop/corridor/00_source/{dwg,dxf,extracted}
mkdir -p ~/Desktop/corridor/data/{raw,gcps,processed}
cd ~/Desktop/corridor
git init
```

Verify:
```bash
find . -type d -not -path './.git*' | sort
```

---

# STEP 2 — Put the reference docs in place

Download these four from the chat, then:

```bash
cd ~/Desktop/corridor

# CLAUDE.md goes at the ROOT — Claude Code reads it automatically
mv ~/Downloads/CLAUDE.md .

# The rest go in docs/
mv ~/Downloads/jaipur_corridor_study.md docs/
mv ~/Downloads/sessions_v2_roundabout.md docs/
mv ~/Downloads/inputs_models_stack.md docs/

ls -la . docs/
```

**Done already.** `CLAUDE.md` has been rewritten around the JDA survey data — six 4-arm
junctions on the Mansarover Metro ↔ Sanganer Stadium corridor. The roundabout block from
`docs/sessions_v2_roundabout.md` is preserved verbatim at the bottom of `CLAUDE.md` under
`# SUPERSEDED`, because the supplied data contains no roundabout. Do not re-append it.

---

# STEP 3 — Move the JDA files in

```bash
cd ~/Desktop/corridor/00_source

# From wherever WhatsApp Desktop saved them
mv ~/Downloads/INT_11-05-2026.rar .
mv ~/Downloads/INT_12-05-2026.rar .
mv ~/Downloads/"mansrover  road final.dwg" dwg/

# Extract the archives
unar -o extracted INT_11-05-2026.rar
unar -o extracted INT_12-05-2026.rar

# See what came out
find extracted -type f | sort
du -sh extracted/*
```

**Send me that `find` output.** The filenames alone tell me whether these are survey point files, DXF, PDFs, or something else.

---

# STEP 4 — Convert the DWG

1. Download **ODA File Converter** — free, from opendesign.com
2. Input folder: `~/Desktop/corridor/00_source/dwg`
3. Output folder: `~/Desktop/corridor/00_source/dxf`
4. Output version: **ACAD 2018**
5. Output type: **DXF**
6. **Tick "Save as ASCII"** — not binary. I cannot read binary DXF.

Then:
```bash
cd ~/Desktop/corridor/00_source/dxf
ls -lh
head -300 *.dxf
```

**Paste me that `head -300`.** `$INSUNITS`, `$EXTMIN` and `$EXTMAX` sit near the top of the header, and their magnitude tells me immediately whether you're in UTM 43N, a local JDA grid, or unreferenced.

---

# STEP 5 — Launch

```bash
cd ~/Desktop/corridor
claude
```

Check what you're on:
```
/status
```

---

# PROMPT ORDER

> **SUPERSEDED.** The session table below describes the original build order, written
> before the survey data arrived and while a roundabout was the subject. Every phase it
> lists is now delivered or explicitly not required, and the module layout it implies is
> not the one in `src/`. `CLAUDE.md` carries the current layout and verification gates.
> Kept for provenance.


**The DWG changes the sequence.** Probing the CAD now moves ahead of building the network, because if that survey is georeferenced you'll use it instead of OSM — sub-metre accuracy instead of 5–10 m.

| # | Session | Needs | Model | Effort |
|---|---|---|---|---|
| 1 | Scaffold + `geo.py` | nothing | `sonnet` | medium |
| **1.5** | **DXF probe** ← new | converted DXF | `sonnet` | medium |
| 2 | Network + ring collapse | exact pin | `opusplan` | **high** |
| 3 | Movement enumeration | Session 2 | `sonnet` | high |
| 4 | Constraint atlas | Session 2 | `sonnet` | medium |
| 5 | Detection + tracking | video | `opusplan` | high |
| 6 | Homography | GCPs | `opus` | **xhigh** |
| 7 | Zone counting + TMC | Sessions 5–6 | `sonnet` | high |
| 8 | Validation + PDF | Session 7 | `sonnet` | medium |
| 9 | Dashboard | Session 8 | `sonnet` | medium |

## How to set these

```
/model sonnet          # or opus, haiku, opusplan
/model opusplan        # Opus plans, Sonnet writes the code
```

You can check your current model anytime by running `/status`.

**Effort is the more useful lever.** Adjusting effort changes how many thinking tokens the model generates while keeping the same per-token rate, so try raising effort before switching to a more expensive model. Levels run low / medium / high / xhigh.

For a one-off hard problem without changing your session setting, type `ultrathink` anywhere in the prompt and Claude Code applies deeper reasoning to that single turn.

**Don't bounce between models mid-session.** Prompt caches are scoped per model, so switching mid-session discards the cache you've built and the next turn re-reads your whole context at full price. Switch at session boundaries.

## Why these choices

- **Sessions 2 and 6 are the hard ones.** Collapsing a roundabout ring into a logical junction, and fitting a homography that has to hold sub-metre — both are easy to get subtly wrong in ways that don't error, they just produce wrong numbers. Worth the compute.
- **Sessions 1, 4, 8, 9 are mechanical.** Scaffolding, plotting, report assembly. Sonnet at medium is the right tool.
- **`opusplan` suits Sessions 2 and 5** because both start with "work out what the structure should be" and end with "now write it."

---

# WHAT TO "ATTACH"

Nothing. Claude Code reads the repo directly.

- **`CLAUDE.md`** at the root is read automatically every session
- **Reference a file** in a prompt with `@`: `@docs/jaipur_corridor_study.md`
- **The docs stay in the repo** — you never re-paste them

So a prompt looks like:

```
Read Phase 2 of @docs/jaipur_corridor_study.md, then build src/network.py.
```

Not: *[pasting 70,000 characters of methodology]*

---

# SESSION 1.5 — DXF probe

Run this after Session 1, once the DXF exists:

```
Write and run src/dxf_probe.py against the converted DXF in
00_source/dxf/. Read Phase 1.2 and Phase 0.2 of
@docs/jaipur_corridor_study.md first.

Print:
  1. DXF version and $INSUNITS
  2. X and Y extents, and the span of each
  3. Total vertex count across all geometric entities
  4. A table of (layer, entity type, count), sorted by count descending
  5. All layer names from the layer table, including empty ones
  6. Classify the likely CRS using the magnitude heuristic in Phase 0.2

Inventory only — do not extract geometry yet.

Jaipur reference: WGS84 26.9124N 75.7873E = UTM43N E578000 N2976000.
If extents are near that, it's EPSG:32643. If near zero, it's
unreferenced and needs GCP fitting.
```

Paste me the output and I'll tell you which coordinate system you're in and which layers we pull.

---

# ORDER OF OPERATIONS TODAY

1. Steps 0–2 — install, repo, docs *(~15 min)*
2. Step 3 — extract the RARs, send me the file list *(~5 min)*
3. Step 4 — convert DWG, send me the header *(~10 min)*
4. Run Session 1 *(~10 min)*
5. Run Session 1.5 once I've seen the header

Steps 2 and 3 are the ones I need output from. Everything else you can just run.
