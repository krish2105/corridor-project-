# Inputs, Models, and Tech Stack
### Mahima / Vande Mataram Circle pilot

---

# PART 1 — THE COMPLETE INPUT LIST

**Five inputs total.** Two unlock Sessions 1–4. Three more unlock Sessions 5–8.

## To start today (2 inputs)

| # | Input | Format | How you get it |
|---|---|---|---|
| 1 | **Exact circle coordinates** | `26.xxxxx, 75.xxxxx` | Long-press the circle centre in Google Maps, copy the numbers |
| 2 | **Confirmed arm count + which are divided** | A sentence | Stand at the circle, or zoom in on satellite view and count |

That is genuinely all. Sessions 1–4 and the constraint atlas need nothing else.

## For the counting half (3 inputs)

| # | Input | Format | Notes |
|---|---|---|---|
| 3 | **Video** | `.mov` / `.mp4`, 4K30 | Stays on your machine. Never uploaded to me — see Part 2 |
| 4 | **GCP pixel coordinates** | CSV: `name, px, py` | Clicked in the Session 6 picker from one video frame |
| 5 | **Two 15-min manual counts** | CSV from the field form | Done at your laptop from your own video, not roadside |

## Later, only if JDA supplies it

DXF sheets, utility drawings, ROW plans, historic counts. None of these block anything. The pilot is designed to need nothing from them.

---

# PART 2 — HOW TO GET THINGS TO ME

This matters, because the obvious approach doesn't work.

## Don't upload the video

90 minutes of 4K is roughly 17 GB. That's far beyond any chat upload limit, and there'd be no point — video processing happens in Claude Code on your own machine, where the GPU is.

## What you actually send me

| Send | Why | Size |
|---|---|---|
| **One video frame as JPEG** | So I can identify GCP candidates and give you their real-world coordinates | ~2 MB |
| **CSV outputs** — arms table, movement table, TMC results | So I can check the numbers and debug | KB |
| **Error logs / tracebacks** | Debugging | Text |
| **A short annotated preview clip** — 30 s | So I can assess detection quality visually | ~50 MB, may still be too large; screenshots work better |
| **Screenshots of the detection overlay** | Fastest way for me to spot tracking problems | ~2 MB |

## The working loop

```
Claude Code on your Mac/PC   →   does the heavy lifting
        ↓ outputs CSV, frames, logs
You upload those here        →   I diagnose, fix logic, write the next prompt
        ↓ revised prompt
Back to Claude Code
```

Claude Code handles the video. I handle the method, the domain decisions, and the debugging. Neither of us needs to move 17 GB.

---

# PART 3 — CAMERA: iPhone 16 Pro

**Yes, it's more than enough.** Genuinely better than most dedicated survey cameras.

## Settings

| Setting | Value | Why |
|---|---|---|
| Resolution | **4K, 30 fps** | 60 fps doubles storage for no benefit; 30 is plenty for tracking |
| Format | **HEVC "High Efficiency"** | Halves the file size |
| Lens | **2x** most likely, test first | 2x on the 16 Pro is a full-quality sensor crop, not digital zoom |
| **Stabilisation** | **OFF** | **Critical.** EIS shifts and crops the frame between moments, which breaks the homography — it assumes a fixed camera |
| Action Mode | **OFF** | Same reason, worse |
| Focus & exposure | **Locked** (long-press to AE/AF lock) | Autofocus hunting mid-recording ruins frames |
| Lens cleaning | Wipe before starting | Obvious, universally forgotten |

## The thermal problem — plan around it

**An iPhone will not record 4K for three hours.** It thermally throttles and stops, and Jaipur heat makes this much worse. Do not plan a single long take.

- Shoot **3 × 30-minute segments** with a few minutes between
- Keep it out of direct sun — shade or a cloth over the body, not the lens
- Remove the case; cases trap heat
- Plug into a power bank, but note that charging generates heat too. Charge between segments rather than during
- Storage: 4K30 HEVC ≈ 190 MB/min → 90 min ≈ 17 GB. Check free space first

**You don't need 3 hours.** A 60–90 minute evening peak is plenty for a pilot, and the validation only needs 2 × 15 minutes from it.

## Mounting

- Tripod, or a phone clamp on a window rail
- **Nothing may move once recording starts.** Not the phone, not the tripod, not the surface it's on
- Tape the tripod legs to the floor if there's any foot traffic
- Frame it once, check all arms are in shot, then don't touch it

## Test before committing

Film **5 minutes**. Open it on your laptop, zoom in, and answer one question: **can you tell an auto-rickshaw from a car?** If yes, the position works. If not, nothing downstream will save it.

---

# PART 4 — MODELS

## Detection

**Start with `YOLO11m`** (Ultralytics). Balanced speed and accuracy, well supported, runs on both your machines.

The COCO classes map partially onto what you need:

| COCO gives you | Maps to |
|---|---|
| `motorcycle` | 2W ✅ |
| `car` | CAR ✅ |
| `bus` | BUS ✅ |
| `truck` | TRUCK / LCV ⚠️ conflated |
| `bicycle` | CYCLE ✅ |
| `person` | pedestrian ✅ |

**It cannot see auto-rickshaws or e-rickshaws at all.** Together those are commonly 20–30% of Jaipur traffic. Session 5 logs the unmapped-detection rate specifically so you can measure that gap with a number rather than assume it.

**Fine-tuning path, in order:**
1. **IDD (India Driving Dataset)**, IIIT Hyderabad — Indian road scenes, includes autorickshaw. Free for research. Start here.
2. **~500 self-annotated frames from your own video** — annotate in Roboflow or CVAT. This second stage is what takes you from "works" to "works on this camera angle." Highest value per hour spent.

Target before trusting counts: mAP@0.5 ≥ 0.80 overall, ≥ 0.70 per class.

## Small-object problem — read this one

Your camera is far away and looking down. Two-wheelers will be small in frame. Standard YOLO inference resizes the whole frame to 640px, which can shrink a 30-pixel motorcycle to nothing.

**Use SAHI** (Slicing Aided Hyper Inference). It tiles the frame into overlapping patches, runs detection on each at full resolution, and merges the results. For distant elevated cameras it's often the difference between 60% and 90% recall on two-wheelers.

Slower — but you're processing recorded video offline, not doing real time. Trade the time.

## Tracking

**ByteTrack**, via the `supervision` library.

It associates *low-confidence* detections as well as high-confidence ones, which is precisely what dense two-wheeler traffic produces. Alternatives:

| Tracker | When |
|---|---|
| **ByteTrack** | **Default.** Best for dense mixed traffic |
| BoT-SORT | Has appearance ReID — better through long occlusion, notably slower |
| DeepSORT | Older, generally superseded by the above |

## Hardware split

| Machine | Job | Why |
|---|---|---|
| **Windows PC, RTX 3060 12GB** | Fine-tuning, SAHI inference, batch video | CUDA substantially beats MPS for both training and sliced inference |
| **MacBook M4 Pro** | Everything else — geometry, topology, analysis, dashboard, outputs | Where you actually work |

---

# PART 5 — TECH STACK, END TO END

## Pipeline

| Layer | Choice | Note |
|---|---|---|
| Language | Python 3.11 | |
| Package manager | `uv` | Faster than pip, better lockfiles |
| Network | `osmnx` ≥ 2.0 | Roundabout ring detection |
| Geometry | `shapely` 2.x, `geopandas` | |
| Graph | `networkx` | |
| Projections | `pyproj` | |
| CAD | `ezdxf` | Only once JDA supplies DXF |
| Detection | `ultralytics` + `sahi` | |
| Tracking | `supervision` | ByteTrack + zone utilities |
| Video/CV | `opencv-python` | Homography, frame IO |
| Data | `pandas`, `pyarrow` | Parquet for track data |

## Storage — start smaller than you think

**Pilot: SQLite + Parquet.** One junction does not need PostGIS. A spatial database for a single roundabout is infrastructure you'd maintain for no benefit.

**Move to PostGIS (Supabase) when** you go multi-junction, or when JDA needs to query it themselves. At that point the schema from the methodology doc drops straight in.

Resist building the database first. It's the most common way this kind of project stalls.

## Dashboard

**Yes, build one — but in Session 9, after the counts work.**

| Layer | Choice | Why |
|---|---|---|
| Framework | **Next.js + React** | You already run this stack |
| Hosting | **Vercel** | Already connected. A shareable link an officer opens on their phone beats any local app |
| Map | **MapLibre GL** | Open source, no API key, handles GeoJSON natively |
| Charts | **Recharts** | Already familiar |
| Data | Static JSON exported from the pipeline | No backend needed for a pilot |

**Why a link matters more than the dashboard.** A JDA officer will not install anything or run a script. They will open a URL on their phone in a meeting. That single property is worth more than any feature you could add.

**Views, in priority order:**
1. Roundabout map with arms labelled and movement volumes
2. TMC matrix — entry arm × exit arm, switchable between vehicles and PCU
3. Time series by 15-min bin, with peak hour marked
4. Vehicle composition
5. Validation panel — the error rates, shown openly rather than buried

That fifth one is not filler. Showing your own error rate on the front page is unusual in Indian traffic reporting and it's the thing that makes an engineer trust the rest.

## Do not build yet

Skipping these is the point, not an oversight:

- PostGIS (one junction doesn't need it)
- Auth (nothing sensitive)
- A backend API (static JSON is enough)
- Multi-junction abstraction (you have one junction)
- Real-time anything (you're processing recorded video)

Each of these is a week you're not spending on getting a validated count.

---

# PART 6 — WHAT THE SKETCH TELLS ME

Reading your drawing: a central island with arms radiating, roughly **one north (with the inbound arrow), one east, one west, and three fanning south/southwest**. The doubled lines on the north, east and west arms read as **divided carriageways with a median**.

Two consequences for the build:

**1. Divided approaches make counting easier, not harder.** Entry and exit are physically separated by the median, so entry and exit zones can't overlap. That's cleaner than an undivided approach where both directions share a surface.

**2. OSM will likely model each divided arm as two separate one-way ways.** So Session 2 may report 12+ edges leaving the ring where there are only 6 logical arms. The code must **group paired one-ways back into one logical arm** before enumerating movements — otherwise you'll get a movement matrix twice the size it should be, with half the entries physically impossible.

That's a real trap and I've noted it for the Session 2 prompt.
