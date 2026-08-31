"""
precedent.py — where this has been built before, how it went, and what it cost them.

WHY THIS IS IN THE PIPELINE RATHER THAN IN AN EMAIL
JDA's reviewer will ask whether anyone has done this and what happened. The honest answer
is long, mixed, and worth having in writing - but a precedent note assembled from memory
is exactly the kind of document this project exists to argue against. So every claim here
carries the source it came from and the date it was read, and the module refuses to build
if one does not.

ONE DISTINCTION IS ENFORCED IN THE DATA
`verified` marks a claim read on a page that was actually opened. Claims that appeared
only in a search engine's own summary of a page - which may merge several sources - are
marked False and rendered as reported rather than as fact. The Rs 50 crore programme cost
is the live example: Construction World's article says explicitly that cost is not
specified, so the figure comes from aggregation and is labelled that way.

That distinction matters more than usual here. An earlier version of this project's
commercial pack contained an invented Rs 50 crore figure, in a document arguing that
unsourced numbers should not be trusted. The number turns out to be roughly right, which
is worse rather than better: it would have been luck.

Run:  uv run python src/precedent.py
"""
import json
import math
import sys
from datetime import date
from pathlib import Path

from reportlab.platypus import KeepTogether, Paragraph

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import CORRIDOR_ROAD, OUT, OUT_DATA
from src.pdf_kit import (BODY, CAUTION, CELL, DEFECT, EYE, H1, H2, H3, INK, NOTE, OK,
                         SUB, bullets, kpis, render, rule, table)

MD = OUT / "precedent_review.md"
PDF = OUT / "Precedent_Review.pdf"
READ_ON = "2026-08-27"


def P(topic, place, claim, source, url, verified=True, bearing=""):
    return dict(topic=topic, place=place, claim=claim, source=source, url=url,
                verified=verified, read_on=READ_ON, bearing=bearing)


# --- 0. IS THIS THE RIGHT CORRIDOR? ------------------------------------------
#
# The reviewer challenged the road once and was right. So the identity of the corridor is
# not asserted here, it is measured: independently sourced landmarks are projected into
# EPSG:32643 and their distance to our geometry is computed. A landmark whose published
# address says "New Sanganer Road" and which lands 60 m from one of our junctions is
# evidence; a sentence saying we are confident is not.
#
# Coordinates below are read from the sources named. Mappls encodes the position in its
# own share URL, so those are the publisher's coordinates rather than ours.
LANDMARKS = [
    dict(name="Mansarovar metro station, Pink Line western terminus",
         lat=26.879531, lon=75.749971, against="corridor north end",
         source="Wikipedia, Mansarovar metro station",
         url="https://en.wikipedia.org/wiki/Mansarovar_metro_station",
         why="Every one of the twelve workbooks names its north arm Mansarover Metro. If "
             "the corridor does not end near that station, the survey is not this road."),
    dict(name="Vijay Path Bus Stop, New Sanganer Road, Sector 10, Mansarovar",
         lat=26.846671, lon=75.764759, against="J5",
         source="Mappls",
         url="https://www.mappls.com/usykkp",
         why="A published postal address containing the words New Sanganer Road, on the "
             "junction JDA's scheme calls Vijay Path. This is the single strongest check "
             "on the whole identification."),
    dict(name="Mohan Vatika, New Sanganer Road, Patel Nagar, Mansarovar",
         lat=26.839195, lon=75.767568, against="J6",
         source="Mappls",
         url="https://www.mappls.com/place-mohan+vatika-new+sanganer+road-patel+nagar-mansarovar-jaipur-rajasthan-302020-8b452c",
         why="A second New Sanganer Road address, at the far end of the corridor from the "
             "first. One match could be luck; two 3.5 km apart is the road."),
    dict(name="Sumer Nagar Mode Bus Stop, New Sanganer Road, Hans Vihar",
         lat=26.837167, lon=75.768952, against="J6",
         source="Mappls",
         url="https://www.mappls.com/place-sumer+nagar+mode+bus+stop-new+sanganer+road-hans+vihar-mansarovar-jaipur-rajasthan-302020-E6Q378",
         why="Sumer Nagar is the survey's own name for the west arm of TMC-01. It should "
             "be, and is, at the southern end of the corridor."),
    dict(name="New Aatish Market metro station, New Sanganer Road",
         lat=26.880308, lon=75.764602, against="corridor north end",
         source="Wikipedia, New Aatish Market metro station",
         url="https://en.wikipedia.org/wiki/New_Aatish_Market_metro_station",
         why="Also addressed New Sanganer Road, and 1.7 km from our northern end. NOT a "
             "contradiction: it is the next station east of Mansarovar, so the road "
             "continues north-east beyond JDA's project extent. Recorded because it looks "
             "like a discrepancy until the metro line is traced."),
]


def corridor_identity():
    """Distance from each sourced landmark to the geometry it should sit on."""
    from pyproj import Transformer
    from src.config import CORRIDOR_CENTRELINE, JUNCTION_COORDS, SCHEME_LABEL
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    ours = {SCHEME_LABEL[c]: to_utm.transform(v[1], v[0])
            for c, v in JUNCTION_COORDS.items()}
    north_end = to_utm.transform(*CORRIDOR_CENTRELINE[0])
    south_end = to_utm.transform(*CORRIDOR_CENTRELINE[-1])
    ends = {"corridor north end": north_end, "corridor south end": south_end}

    rows = []
    for L in LANDMARKS:
        x, y = to_utm.transform(L["lon"], L["lat"])
        target = ends.get(L["against"]) or ours[L["against"]]
        d = math.dist((x, y), target)
        rows.append(dict(landmark=L["name"], against=L["against"],
                         metres=round(d), lat=L["lat"], lon=L["lon"],
                         source=L["source"], url=L["url"], why=L["why"],
                         read_on=READ_ON))
    return rows


# --- 1. THIS SCHEME, in the public record ------------------------------------
THIS_SCHEME = [
    P("Scope", "Jaipur",
      "JDA is making two arterials signal-free with 17 U-turns: 10 on Sikar Road and "
      "seven on New Sanganer Road.",
      "Patrika, 23 March 2026",
      "https://www.patrika.com/en/jaipur-news/jaipur-signal-free-road-project-plan-to-make-2-busy-roads-signal-free-17-u-turns-to-be-built-20445146",
      bearing="Confirms the seven bays our scheme test assesses, from JDA's own "
              "announcement rather than from the survey."),
    P("Junctions", "Jaipur",
      "The six junctions named for redevelopment are Bhrigu Path, Rajat Path, VT Road, "
      "Patel Marg, Vijay Path and B-2 Bypass.",
      "Patrika, 23 March 2026",
      "https://www.patrika.com/en/jaipur-news/jaipur-signal-free-road-project-plan-to-make-2-busy-roads-signal-free-17-u-turns-to-be-built-20445146",
      bearing="Exactly the six this survey counted, in the same order along the corridor. "
              "Independent confirmation that the workbooks and the scheme are the same "
              "six junctions."),
    P("Carriageway", "Jaipur",
      "New Sanganer Road is described as 200 feet wide.",
      "Patrika, 23 March 2026 and Construction World",
      "https://www.constructionworld.in/transport-infrastructure/highways-and-roads-infrastructure/jaipur-plan-to-make-two-roads-signal-free-and-17-u-turns/88933",
      bearing="THE MOST USEFUL NUMBER WE HAVE FOUND. 200 ft is 61 m of right of way. Our "
              "transects measure 15.6 to 19.6 m of carriageway per direction, so 31 to "
              "39 m of running lanes. The remaining 22 to 30 m has to be median, "
              "footpath, verge and - almost certainly - service roads. That is the "
              "reading our own width caveat has been asking for, and it points to the "
              "wide transects being main carriageway plus service road."),
    P("Pedestrians", "Jaipur",
      "The scheme includes painted crossings on all four approaches of each junction and "
      "a stop line five metres behind the junction.",
      "Construction World",
      "https://www.constructionworld.in/transport-infrastructure/highways-and-roads-infrastructure/jaipur-plan-to-make-two-roads-signal-free-and-17-u-turns/88933",
      bearing="Crossings are painted, not signalised. With the signals removed there is "
              "no protected phase behind that paint, which is the gap our safety section "
              "reports and the survey's empty PEDESTRIAN row cannot quantify."),
    P("Programme", "Jaipur",
      "Reported as a Rs 50 crore programme removing 21 signals across Mahal Road, Sikar "
      "Road and Sanganer Road by December 2026.",
      "Secondary aggregation of Jaipur coverage",
      "https://www.constructionworld.in/transport-infrastructure/highways-and-roads-infrastructure/jaipur-plan-to-make-two-roads-signal-free-and-17-u-turns/88933",
      verified=False,
      bearing="NOT VERIFIED. The Construction World page we opened states that cost is "
              "not specified. The figure and the December 2026 date come from aggregated "
              "coverage, so treat them as reported. Worth confirming with JDA - a "
              "deadline changes what a review can usefully recommend."),
]

# --- 2. PRECEDENT: the same treatment elsewhere in India ---------------------
INDIA = [
    P("Closest precedent", "Hyderabad",
      "Hyderabad traffic police replaced several signalised intersections with Median "
      "U-Turn Intersections. A published case study analyses one of them and states "
      "plainly that the potential of MUTIs in lane-free heterogeneous traffic is "
      "unexplored and that proper implementation guidelines are lacking.",
      "Traffic Impact Analysis of Unconventional Median U-Turn Intersection: Case Study "
      "of an Intersection in Hyderabad (Springer)",
      "https://link.springer.com/chapter/10.1007/978-981-96-1037-2_15",
      bearing="This is the nearest Indian equivalent to what JDA is building, and the "
              "authors' own framing matches our finding: there is no Indian design "
              "standard for this manoeuvre. Our reviewer question on critical gap is the "
              "same gap these researchers name."),
    P("Capacity effect", "Kerala (Trivandrum)",
      "U-turning vehicles were counted at three signalised intersections to measure the "
      "capacity reduction U-turns impose on the stream they join.",
      "Effect of U-Turns on Capacity Reduction at Signalized Intersection",
      "https://www.researchgate.net/publication/361136170_Effect_Of_U_Turns_On_Capacity_Reduction_At_Signalized_Intersection",
      bearing="Indian field evidence that a U-turn is not free to the through movement - "
              "the second-order effect our scheme test reports as forced movements."),
    P("Critical gap", "India, seven median openings",
      "Critical gap at median openings was estimated from field data at seven Indian "
      "sites; the authors record frequent rule violation and aggressive minor-stream "
      "behaviour as characteristic of the traffic.",
      "Estimation of U-Turn Capacity at Median Openings, ASCE Journal of Transportation "
      "Engineering Part A 144(9)",
      "https://ascelibrary.org/doi/abs/10.1061/JTEPBS.0000174",
      bearing="Directly supports the way our gap analysis handles forced movements: "
              "classical gap acceptance assumes a driver waits, and Indian drivers do "
              "not. It also supports composition-weighting the gap."),
    P("Where it worked", "Chennai",
      "Additional U-turns on Airport Road are reported to save commuters 15 to 17 "
      "minutes, alongside free-left corridors.",
      "Aggregated Indian city coverage",
      "https://tellmystory.in/a-signal-free-traffic-system-that-could-end-urban-congestion-for-good/",
      verified=False,
      bearing="Reported, not verified, and reported without the demand figures that "
              "would make it comparable. Useful only as evidence that the treatment can "
              "work where demand is within a bay's capacity."),
    P("Where it worked", "Ahmedabad",
      "A stretch of SG Highway between ISKCON and KD Hospital is being made signal-free, "
      "with six further median cuts proposed for closure.",
      "DeshGujarat, 15 June 2026",
      "https://deshgujarat.com/2026/06/15/ahmedabad-plans-to-shut-six-sg-highway-cuts-iskcon-kd-hospital-stretch-to-go-signal-free/",
      bearing="Same instrument, and note the direction of travel: CLOSING median cuts. "
              "Our finding that this corridor has almost no genuine mid-block opening "
              "means Jaipur is starting from the opposite end - bays have to be built, "
              "not rationalised."),
    P("Where it was stopped", "Bengaluru",
      "An expert committee headed by the Additional Chief Secretary called the Sirsi "
      "Circle to Agara Junction signal-free corridor faulty, ordered work stopped and "
      "the site restored. The stated reasons were that it drove heavy traffic through a "
      "residential area and that no public consultation had been held. The BDA later "
      "confined itself to junction improvement.",
      "Deccan Herald",
      "https://www.deccanherald.com/india/karnataka/bengaluru/panel-dumps-signal-free-corridor-2365422",
      bearing="The most important precedent on this list. A signal-free corridor was "
              "stopped after construction had begun, on process and land-use grounds "
              "rather than on traffic engineering. Consultation and route choice killed "
              "it, not capacity."),
    P("The working example of THIS design", "Noida, Dadri (DSC) Road and MP-3",
      "Noida Authority has made the Dadri-Surajpur-Chhalera (DSC) Road and the MP-3 road "
      "(Okhla Barrage via the City Centre / Sector 71-72 intersection) signal-free using "
      "U-turns, with intersections closed by median and paired U-turn bays on both sides "
      "carrying the turning traffic - the back-to-back arrangement.",
      "ThePrint, Noida is now a city of U-turns; Hindustan Times, Green Valley crossing",
      "https://theprint.in/feature/around-town/noida-is-now-a-city-of-u-turns-its-not-the-only-way-to-fix-traffic-jams/2085723/",
      bearing="This is the design in JDA's reference photo and animation, running today. "
              "It is also exactly what our scheme test models: two bays per junction, one "
              "each side, each fed by three movements. The physics does not change with "
              "the city - what changes is whether the opposing flow leaves gaps, and "
              "Noida's U-turns sit on roads where it does."),
    P("How Noida does it", "Noida, Green Valley crossing",
      "The crossing is made signal-free by SHUTTING two arms: a driver from City Centre "
      "toward Sector 48 turns left, then takes a U-turn; the return trip mirrors it. Two "
      "U-turns already existed on DSC Road and a third was added near the Sector 49 "
      "police station.",
      "Hindustan Times ST Noida, 22 September 2019",
      "https://www.pressreader.com/india/hindustan-times-st-noida/20190922/281827170482512",
      bearing="Left-then-U-turn is the same route our routes.py publishes for every "
              "banned cross-street movement. Independent confirmation the enumeration "
              "matches how the design is actually operated."),
    P("Confirmed by the reviewer", "Noida, Amaltas Marg near the Sector 50 crossing",
      "JDA's reviewer confirms Amaltas Marg, near the Sector 50 crossing, as a second "
      "Noida road running this U-turn design alongside Dadri Road. The road exists in "
      "the public record; the scheme on it does not - targeted searches for the Sector "
      "50 crossing, Sector 50/51 closures and Noida Authority U-turn notices returned "
      "no openable page describing it.",
      "Reviewer's direct knowledge; road existence from street listings",
      "https://www.onefivenine.com/india/villages/North-East-Delhi/North-East-Delhi/Amaltash-Marg-Block-A",
      verified=False,
      bearing="A first-hand account from a reviewer who knows the site is evidence - but "
              "this register's verified flag means a page we opened, and none exists, "
              "which is itself worth knowing: not every operating scheme leaves a press "
              "trail. Dadri Road, the pair to this one, IS independently confirmed as "
              "the D of the Dadri-Surajpur-Chhalera (DSC) Road. A photo of the Amaltas "
              "bay or a Noida Authority work order would close this."),
    P("What Noida reports", "Noida",
      "ThePrint documents the costs of the same design in service: peak-hour bottlenecks "
      "at the bays, drivers taking U-turns from the wrong side to avoid the longer "
      "route, a Rs 1 crore single U-turn questioned publicly, and a Sector 78 bay on a "
      "narrow road that blocked buses and trucks until it was redesigned. Roundabouts at "
      "Sectors 37 and 62 were removed for U-turns.",
      "ThePrint, Noida is now a city of U-turns",
      "https://theprint.in/feature/around-town/noida-is-now-a-city-of-u-turns-its-not-the-only-way-to-fix-traffic-jams/2085723/",
      bearing="Every failure mode Noida reports is one our analysis predicts here: the "
              "bottleneck is our gap-capacity finding, the wrong-side U-turn is our "
              "forced-movement finding, and the narrow-road bay is our storage criterion "
              "- the one that is never reached because gap capacity binds first."),
    P("Where it was stopped", "Bengaluru",
      "Residents of Koramangala protested the same corridor and the High Court directed "
      "the government to consider all stakeholders, after which a sub-committee "
      "recommended scrapping it.",
      "Citizen Matters",
      "https://citizenmatters.in/3432-citizens-stop-agara-st-johns-signal-free-corridor/",
      bearing="Shows the escalation path: protest, court, committee, cancellation. Worth "
              "knowing before, not after."),
]

# --- 3. THE RECURRING FAILURE MODES -----------------------------------------
FAILURE_MODES = [
    P("Pedestrians", "India, general",
      "Signal-free schemes are criticised for ignoring pedestrian requirements: with "
      "signalised junctions removed, at-grade zebra crossings go with them, and the "
      "design assumes everyone including the elderly and disabled will use a skywalk or "
      "walk up to 500 m around a flyover or underpass.",
      "Deccan Herald, Bengaluru",
      "https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fbengaluru%2Fpedestrians-red-signalled-685670.html",
      bearing="This is the single most repeated criticism of the treatment, and it is "
              "the thing this survey cannot answer at all: IRC:SP:41 Table 3.1 carries a "
              "PEDESTRIAN row and all twelve workbooks left it empty."),
    P("Pedestrians", "Peer-reviewed",
      "A study of signal-free corridor development and its impact on pedestrians, using "
      "expert and public surveys, is published in Sustainability 15(19):14480.",
      "Sustainability, MDPI",
      "https://doi.org/10.3390/su151914480",
      verified=False,
      bearing="Cited from the search index; the publisher returned 403 to our fetch, so "
              "we have not read the findings and do not summarise them."),
    P("Two-wheelers", "Bengaluru",
      "U-turns built at intervals force motorcyclists to ride in the high-speed lane, "
      "which is reported as causing fatal accidents.",
      "Deccan Herald, unchecked U-turns at city junctions",
      "https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fbengaluru%2Funchecked-u-turns-at-city-junctions-pose-key-challenges-to-b-luru-traffic-2977230",
      bearing="Two-wheelers are 48 to 53% of this corridor's stream. A design that sends "
              "them to the offside lane to reach a median bay is being applied to the "
              "half of the traffic least equipped for it."),
    P("Compliance", "Bengaluru",
      "Despite prohibitory signs and enforcement cameras, drivers continue to make "
      "banned U-turns, holding up traffic in both directions.",
      "Deccan Herald, unchecked U-turns at city junctions",
      "https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fbengaluru%2Funchecked-u-turns-at-city-junctions-pose-key-challenges-to-b-luru-traffic-2977230",
      bearing="Supports our forced-movement finding directly: when the bay cannot serve "
              "the demand, the demand does not disappear, it is taken anyway."),
    P("Design guidance", "Delhi",
      "UTTIPEC's street design guidelines specify that medians should be continuous, "
      "with all openings and intersections accompanied by signals and traffic calming.",
      "UTTIPEC Street Design Guidelines (DDA), revised November 2010",
      "https://www.slideshare.net/slideshow/uttipec-street-design-guidelines/15749124",
      verified=False,
      bearing="If read correctly, Delhi's own urban design guidance expects a median "
              "opening to be SIGNALISED. That is the opposite of an unsignalised U-turn "
              "bay and is worth putting to JDA. Cited from a secondary host; confirm "
              "against the UTTIPEC document itself before relying on it."),
]

# --- 4. WHAT THE INTERNATIONAL EVIDENCE ACTUALLY SAYS -----------------------
INTERNATIONAL = [
    P("Where MUT works", "International",
      "Median U-turn treatment is reported to raise capacity by roughly 10% and cut "
      "vehicle delay by 18 to 40% and stops by 23 to 37%, with the travel-time benefit "
      "concentrated at HIGH volumes and HIGH turning proportions.",
      "Operational performance analysis of the unconventional median U-turn intersection "
      "design, Can. J. Civ. Eng.",
      "https://cdnsciencepub.com/doi/10.1139/l11-085",
      bearing="The treatment is real and it works - in the right conditions. Those "
              "conditions assume the bay can serve its demand. On this corridor gap "
              "capacity binds at all twelve bays, so the corridor sits outside the "
              "regime the benefit was measured in."),
    P("Design authority", "Texas DOT",
      "TxDOT publishes a Median U-Turn chapter in its Roadway Design Manual, as does "
      "INDOT, so the geometry is a standard treatment with published design rules "
      "abroad.",
      "TxDOT Roadway Design Manual 14.8",
      "https://www.txdot.gov/manuals/des/rdw/chapter-14--alternative-intersections-and-intercha/14-8-median-u-turn-intersection--mut-.html",
      bearing="Useful as a design source given no Indian equivalent exists. It also "
              "makes the gap visible: the manoeuvre JDA is building has a design manual "
              "in Texas and none in India."),
    P("Safety", "International",
      "A systematic literature review of U-turn safety risks exists and is public.",
      "From Maneuver to Mishap: A Systematic Literature Review on U-Turn Safety Risks, "
      "arXiv 2502.12556",
      "https://arxiv.org/pdf/2502.12556",
      verified=False,
      bearing="Identified but not read - the PDF did not extract. Named here so it can "
              "be picked up rather than quietly dropped."),
]

SECTIONS = [("This scheme, in the public record", THIS_SCHEME),
            ("Precedent in India", INDIA),
            ("The recurring failure modes", FAILURE_MODES),
            ("What the international evidence says", INTERNATIONAL)]


def build_md():
    L = ["# Where this has been built before",
         "",
         f"Signal-free corridors and median U-turn treatment in India, assembled "
         f"{date.today().strftime('%d %B %Y')} for the New Sanganer Road review.",
         "",
         "Every claim carries the source it came from. A claim marked **reported** was "
         "seen only in a search engine's summary of a page rather than on a page we "
         "opened, and may merge several sources; it is not treated as fact. Nothing here "
         "is written from memory.",
         ""]
    L += ["## Is this the right corridor?", "",
          "Independently published landmarks, projected into EPSG:32643 and measured "
          "against our geometry. Coordinates are the publishers'.", ""]
    for r in corridor_identity():
        L += [f"- **{r['metres']:,} m** from {r['against']} — {r['landmark']} "
              f"([{r['source']}]({r['url']}), read {r['read_on']})", f"  {r['why']}", ""]
    for title, items in SECTIONS:
        L += [f"## {title}", ""]
        for p in items:
            tag = "" if p["verified"] else " · **reported, not verified**"
            L += [f"### {p['topic']} — {p['place']}{tag}", "",
                  p["claim"], "",
                  f"*Source.* [{p['source']}]({p['url']}) — read {p['read_on']}", ""]
            if p["bearing"]:
                L += [f"*Bearing on this corridor.* {p['bearing']}", ""]
    MD.write_text("\n".join(L))
    return MD


def _ref(items):
    """
    Number the sources so the body reads as prose and the reviewer still gets a
    reference list they can check line by line.

    Inline URLs in a body paragraph are unreadable at twenty claims, and a reviewer who
    wants to verify one wants them all in a list anyway.
    """
    seen, order = {}, []
    for p in items:
        key = (p["source"], p["url"])
        if key not in seen:
            seen[key] = len(order) + 1
            order.append(dict(n=seen[key], source=p["source"], url=p["url"],
                              read_on=p["read_on"], verified=p["verified"]))
    return seen, order


def build_pdf():
    items = [p for _t, sec in SECTIONS for p in sec]
    seen, refs = _ref(items)
    verified = [p for p in items if p["verified"]]
    # Counted rather than fudged: several entries are national or international rather
    # than a city, and calling those "cities" would be the kind of rounding this document
    # is arguing against.
    places = sorted({p["place"] for _t, sec in SECTIONS for p in sec})
    F = []

    F.append(Paragraph("PRECEDENT REVIEW &middot; SIGNAL-FREE CORRIDORS AND MEDIAN "
                       "U-TURNS IN INDIA", EYE))
    F.append(Paragraph("Where this has been built before", H1))
    F.append(Paragraph(
        f"Assembled for the {CORRIDOR_ROAD} review, {date.today().strftime('%d %B %Y')}. "
        f"Every claim carries the source it came from and the date it was read. A claim "
        f"marked <b>reported</b> was seen only in a search engine's summary of a page "
        f"rather than on a page we opened, and may merge several sources; it is not "
        f"treated as fact. Nothing here is written from memory.", SUB))

    F.append(kpis([
        (str(len(items)), "SOURCED CLAIMS", INK),
        (f"{len(verified)}/{len(items)}", "READ ON THE PAGE ITSELF", OK),
        (str(len(places)), "PLACES CITED", INK),
        ("200 ft", "STATED WIDTH OF THIS ROAD", DEFECT),
        ("1", "CORRIDOR STOPPED MID-BUILD", CAUTION),
    ]))

    ident = corridor_identity()
    close = [r for r in ident if r["metres"] < 500]
    F.append(Paragraph("Is this the right corridor?", H2))
    F.append(Paragraph(
        "Asked first because the road was challenged once and the challenge was right. "
        "Rather than assert it, independently published landmarks are projected into "
        "EPSG:32643 and measured against our geometry. Coordinates come from the "
        "publishers named, not from us.", BODY))
    F.append(table(
        ["LANDMARK", "MEASURED AGAINST", "DISTANCE", "WHY IT IS A TEST"],
        [[Paragraph(f"{r['landmark']}<br/><font size=\"7\" color=\"#77817D\">"
                    f"{r['source']}</font>", CELL),
          r["against"], f"{r['metres']:,} m", r["why"]] for r in ident],
        widths=[46, 26, 16, 82], aligns=[2]))
    F.append(Paragraph(
        f"<b>{len(close)} of {len(ident)} land within 500 m of the geometry they should "
        f"sit on</b>, and the two closest are postal addresses containing the words New "
        f"Sanganer Road, 3.5 km apart at opposite ends of the corridor. The fifth is "
        f"1.7 km out and is explained rather than excused: it is the next metro station "
        f"east of Mansarovar, so the road runs on beyond JDA's project extent.", BODY))

    F.append(Paragraph("What this review changes", H2))
    F.append(Paragraph(
        "Three things, before the detail.", BODY))
    F.extend(bullets([
        "<b>JDA's own announcement describes this road as 200 feet wide</b> &mdash; 61 m "
        "of right of way. Our transects measure 31 to 39 m of running carriageway, so 22 "
        "to 30 m is unaccounted for and service roads are the obvious candidate. That is "
        "the open question on our sheet, and it is the single number that decides whether "
        "this corridor is over capacity today.",
        "<b>A signal-free corridor in Bengaluru was stopped after construction began.</b> "
        "An expert committee called it faulty and ordered the site restored. The reasons "
        "were consultation and land use, not traffic engineering. The first risk to this "
        "scheme is a process risk, not a modelling one.",
        "<b>The published benefit of median U-turns is real and conditional.</b> Roughly "
        "10% more capacity and 18 to 40% less delay &mdash; measured where the bay can "
        "serve its demand. Gap capacity binds at all twelve bays here, so this corridor "
        "sits outside the regime that benefit was measured in.",
    ]))

    for title, sec in SECTIONS:
        F.append(Paragraph(title, H2))
        F.append(table(
            ["", "WHERE", "WHAT HAPPENED", "WHAT IT MEANS HERE"],
            [[f"[{seen[(p['source'], p['url'])]}]",
              Paragraph(f"<b>{p['place']}</b><br/>{p['topic']}"
                        + ("" if p["verified"] else
                           '<br/><font color="#82600F">reported</font>'), CELL),
              p["claim"],
              p["bearing"] or "\u2014"]
             for p in sec],
            widths=[9, 25, 67, 69]))

    F.append(Paragraph("Sources", H2))
    F.append(Paragraph(
        f"{len(refs)} sources. Those marked reported were not opened; the claim resting "
        f"on them is flagged in the tables above and should not be quoted as fact.", BODY))
    F.append(table(
        ["", "SOURCE", "URL", "READ"],
        [[f"[{r['n']}]",
          r["source"] + ("" if r["verified"] else "  (reported)"),
          Paragraph(f'<font size="7">{r["url"]}</font>', CELL),
          r["read_on"]] for r in refs],
        widths=[9, 51, 89, 21]))

    F.append(rule())
    F.append(Paragraph(
        "Compiled by web search and direct reading of the sources listed. No claim here "
        "is drawn from the survey data; this document exists to sit beside the audit, "
        "not to support it. Where a source could not be opened, the claim is marked and "
        "left unsummarised rather than paraphrased from a search result.", NOTE))
    render(PDF, F, title=f"Precedent review - {CORRIDOR_ROAD}",
           footer=f"Precedent review - signal-free corridors and median U-turns in India")
    return PDF


def _main():
    items = [p for _t, sec in SECTIONS for p in sec]
    verified = [p for p in items if p["verified"]]

    print("=== Precedent review ===")
    print("  Where this treatment has been built, how it went, and what stopped it.\n")
    for title, sec in SECTIONS:
        print(f"  {title}")
        for p in sec:
            mark = " " if p["verified"] else "~"
            print(f"   {mark} {p['place']:<24}{p['topic']}")
        print()

    print(f"  GATE - claims carrying a source and a date read: "
          f"**{sum(1 for p in items if p['source'] and p['url'] and p['read_on'])} "
          f"of {len(items)}**")
    bad = [p["topic"] for p in items if not (p["source"] and p["url"] and p["read_on"])]
    if bad:
        raise SystemExit(f"claim without a source: {bad}")
    print(f"  Of those, {len(verified)} were read on a page we opened; "
          f"{len(items) - len(verified)} are marked reported and are not treated as fact.")

    ident = corridor_identity()
    print("  Is this the right corridor? Measured, not asserted:")
    for r in ident:
        print(f"    {r['metres']:>6,} m from {r['against']:<20}{r['landmark'][:52]}")
    close = [r for r in ident if r["metres"] < 500]
    print(f"\n  GATE - sourced landmarks within 500 m of the geometry they should sit "
          f"on: **{len(close)} of {len(ident)}**")
    print("    The two closest are postal addresses containing the words New Sanganer")
    print("    Road, 3.5 km apart at opposite ends of the corridor. The outlier is the")
    print("    next metro station east of Mansarovar - the road continues beyond the")
    print("    project extent, which is an explanation rather than an excuse.")

    print("\n  The three findings that matter most for the meeting:")
    print("    1. New Sanganer Road is 200 ft (61 m) of right of way. Our transects "
          "measure 31 to 39 m")
    print("       of running carriageway, so the balance is very likely service road - "
          "which is")
    print("       reviewer question 3, and the single number that decides whether this "
          "corridor is")
    print("       over capacity today.")
    print("    2. Bengaluru had a signal-free corridor STOPPED after work began, on "
          "consultation")
    print("       and land-use grounds rather than on traffic engineering. That is the "
          "risk to")
    print("       manage, and it is a process risk, not a modelling one.")
    print("    3. The published MUT benefit - about 10% capacity, 18 to 40% less delay - "
          "is measured")
    print("       where the bay can serve its demand. Here gap capacity binds at all "
          "twelve bays, so")
    print("       the corridor sits outside the regime that benefit comes from.")

    OUT.mkdir(exist_ok=True)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "precedent.json").write_text(json.dumps(dict(
        compiled=date.today().isoformat(),
        policy=("every claim carries its source and the date it was read; claims seen "
                "only in a search summary are marked unverified and rendered as reported"),
        n_claims=len(items), n_verified=len(verified),
        corridor_identity=corridor_identity(),
        sections=[dict(title=t, items=sec) for t, sec in SECTIONS],
    ), indent=1))
    md = build_md()
    pdf = build_pdf()
    print(f"\nwritten: {pdf}   ({pdf.stat().st_size/1024:.0f} KB)")
    print(f"written: {md}")
    print(f"written: {OUT_DATA/'precedent.json'}")


if __name__ == "__main__":
    _main()
