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
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import OUT, OUT_DATA

MD = OUT / "precedent_review.md"
READ_ON = "2026-08-27"


def P(topic, place, claim, source, url, verified=True, bearing=""):
    return dict(topic=topic, place=place, claim=claim, source=source, url=url,
                verified=verified, read_on=READ_ON, bearing=bearing)


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
        sections=[dict(title=t, items=sec) for t, sec in SECTIONS],
    ), indent=1))
    md = build_md()
    print(f"\nwritten: {md}")
    print(f"written: {OUT_DATA/'precedent.json'}")


if __name__ == "__main__":
    _main()
