#!/usr/bin/env python3
"""
Build Improvement Plan - Generalized orchestration script.
Takes a team name, discovers sprints, calculates KPIs, and outputs
a complete improvement plan JSON ready for HTML generation.

Usage:
  python build_improvement_plan.py --team COM --data-dir ./data --output plan.json
  python build_improvement_plan.py --team COM --data-dir ./data --output plan.json --calc-script ./scripts/calculate_kpis.py
"""

import subprocess, json, sys, re, os, argparse
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="Build sprint improvement plan for a team")
    parser.add_argument("--team", required=True, help="Team prefix (e.g., COM, CRM, Atom)")
    parser.add_argument("--data-dir", required=True, help="Directory containing hTask.csv, hEpic.csv, hInitiative.csv, hSprints.csv")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--calc-script", default=None, help="Path to calculate_kpis.py (defaults to same directory as this script)")
    parser.add_argument("--num-sprints", type=int, default=4, help="Number of recent closed sprints to analyze (default: 4)")
    return parser.parse_args()

def find_calc_script(explicit_path):
    if explicit_path:
        return explicit_path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "calculate_kpis.py")

def discover_sprints(calc_script, data_dir, team, num_sprints):
    """Find the last N closed sprints for the team."""
    result = subprocess.run(
        ["python3", calc_script,
         "--tasks", os.path.join(data_dir, "hTask.csv"),
         "--epics", os.path.join(data_dir, "hEpic.csv"),
         "--initiatives", os.path.join(data_dir, "hInitiative.csv"),
         "--sprints", os.path.join(data_dir, "hSprints.csv"),
         "--find-sprints", team,
         "--last-n", str(num_sprints)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR discovering sprints: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(result.stdout)
    return data.get("sprints", [])

def calculate_kpis_for_sprint(calc_script, data_dir, sprint_name):
    """Run KPI calculation for a single sprint."""
    result = subprocess.run(
        ["python3", calc_script,
         "--tasks", os.path.join(data_dir, "hTask.csv"),
         "--epics", os.path.join(data_dir, "hEpic.csv"),
         "--initiatives", os.path.join(data_dir, "hInitiative.csv"),
         "--sprints", os.path.join(data_dir, "hSprints.csv"),
         "--sprint-name", sprint_name],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR calculating KPIs for {sprint_name}: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)

def compute_trend(kpi_name, values):
    """Determine if a KPI is improving, worsening, or stable."""
    if len(values) < 2:
        return "stable"
    first_half = sum(values[:len(values)//2]) / max(len(values)//2, 1)
    second_half = sum(values[len(values)//2:]) / max(len(values) - len(values)//2, 1)
    diff = second_half - first_half
    pct = abs(diff / first_half * 100) if first_half != 0 else 0
    if pct < 5:
        return "stable"
    # For SC and RC, higher is better. For SCT, EWIP, ECT, lower is better.
    if kpi_name in ["SC", "RC"]:
        return "improving" if diff > 0 else "worsening"
    else:
        return "improving" if diff < 0 else "worsening"

def zone_for(kpi_name, value):
    """Determine the zone (GREEN/YELLOW/RED) for a KPI value."""
    thresholds = {
        "SC":   {"GREEN": (80, 100), "YELLOW": (50, 79), "RED": (0, 49)},
        "RC":   {"GREEN": (50, 100), "YELLOW": (35, 49), "RED": (0, 34)},
        "SCT":  {"GREEN": (1, 6),    "YELLOW": (7, 9),   "RED": (10, 999)},
        "EWIP": {"GREEN": (1, 3),    "YELLOW": (4, 5),   "RED": (6, 999)},
        "ECT":  {"GREEN": (1, 5),    "YELLOW": (6, 8),   "RED": (9, 999)},
    }
    for zone, (lo, hi) in thresholds[kpi_name].items():
        if lo <= value <= hi:
            return zone
    return "RED"

def detect_feedback_loops(kpi_values):
    """Detect dangerous feedback loops from KPI trends."""
    loops = []
    ewip = kpi_values["EWIP"]
    sct = kpi_values["SCT"]

    if len(ewip) >= 3 and ewip[-1] >= ewip[-2] and ewip[-2] >= ewip[-3]:
        loops.append({
            "name": "WIP Death Spiral",
            "pattern": "EWIP up -> SCT up (+50%) -> ECT up (+70%) -> EWIP up (+55%)",
            "severity": "HIGH",
            "evidence": f"EWIP has been {ewip[-3]} -> {ewip[-2]} -> {ewip[-1]} over 3 sprints"
        })

    sct_avg = sum(sct) / len(sct) if sct else 0
    if sct and sct[-1] > sct_avg * 1.5:
        loops.append({
            "name": "Delivery Stall",
            "pattern": "SCT up -> SC down (-60%) -> ECT up -> RC down (-40%)",
            "severity": "MEDIUM",
            "evidence": f"SCT {sct[-1]:.1f}d exceeds 150% of rolling avg {sct_avg:.1f}d"
        })

    return loops

def build_improvement_plan(latest_kpis, team):
    """Generate a 6-sprint improvement plan based on current KPI state."""
    current = {
        "EWIP": latest_kpis["EWIP"]["value"],
        "SC": latest_kpis["SC"]["value"],
        "SCT": latest_kpis["SCT"]["value"],
        "RC": latest_kpis["RC"]["value"],
        "ECT": latest_kpis["ECT"]["value"],
    }
    zones = {k: latest_kpis[k]["zone"] for k in current}

    # Determine priority order
    # If EWIP RED -> start there (highest leverage)
    # If SCT RED but EWIP OK -> story breakdown
    # If SC RED but others OK -> planning discipline
    # RC RED -> usually symptom, fix others first
    # ECT RED -> follows from SCT+EWIP

    sprints = []
    prev = dict(current)

    # Sprint plan templates based on priority
    plan_templates = [
        {
            "theme": "Reduce WIP - Stop Starting, Start Finishing",
            "focus": "EWIP",
            "actions": [
                "Set a hard WIP limit: only 3-4 epics actively In Progress at any time. Move backlog-status epics out of sprints entirely.",
                "Run a triage session to identify the top 3-4 epics for next sprint. Every other epic goes back to backlog with no sprint tasks.",
                "Introduce 'one in, one out' rule: no new epic work starts until a current epic reaches Done."
            ],
            "watch": ["Track active-only EWIP weekly. Target should be visible by mid-sprint.", "If EWIP doesn't drop, escalate WIP limits and involve product owner in prioritization."]
        },
        {
            "theme": "Improve Story Breakdown and Estimation",
            "focus": "SCT",
            "actions": [
                "Break any story estimated at >5 days into 2-3 smaller stories before pulling into sprint.",
                "Review SCT distribution: look for bimodal pattern (many small + few very large). Target all stories under 5 days.",
                "Protect sprint scope: no mid-sprint additions unless something is removed first."
            ],
            "watch": ["SCT median should drop below 3 days.", "If stories >10d still appear, breakdown discipline isn't sticking."]
        },
        {
            "theme": "Stabilize Sprint Predictability",
            "focus": "SC",
            "actions": [
                "Commit to only 80% sprint capacity: leave 20% buffer for unplanned work and context switching.",
                "Close at least 1-2 long-running epics. Either finish or descope and close.",
                "Start sprint retrospectives focused on completion: what prevented tasks from finishing in-sprint?"
            ],
            "watch": ["SC should cross 55%. If spillover rate stays above 30%, sprint planning is still too optimistic.", "Check if unplanned work is being tracked and measured."]
        },
        {
            "theme": "Strengthen Roadmap Alignment",
            "focus": "RC",
            "actions": [
                "Ensure 60%+ of sprint tasks tie to quarterly-labelled epics. Push non-roadmap work to dedicated slack time.",
                "Review epic portfolio: move stale Backlog epics out of active consideration.",
                "Align with product on next quarter priorities: fewer, bigger bets instead of many small epics."
            ],
            "watch": ["RC strict (quarterly-labelled only) should rise above 20%.", "If it stays flat, the labelling or roadmap process needs fixing."]
        },
        {
            "theme": "Sustain and Optimize Delivery Flow",
            "focus": "ECT",
            "actions": [
                "Make WIP limits and sprint capacity rules permanent team agreements, not just temporary experiments.",
                "Set up automated KPI tracking: run this evaluation every sprint to catch regressions early.",
                "Celebrate wins: if the team hits GREEN on 3+ KPIs, acknowledge the improvement publicly."
            ],
            "watch": ["All 5 KPIs should be YELLOW or better.", "If any KPI regresses to RED, investigate immediately."]
        },
        {
            "theme": "Continuous Improvement Culture",
            "focus": "ALL",
            "actions": [
                "Review the full improvement journey: compare baseline to current state across all 5 KPIs.",
                "Identify the next level of optimization: is there a new bottleneck that emerged as old ones were resolved?",
                "Share learnings with other teams: document what worked as a playbook for the organization."
            ],
            "watch": ["Stability is the goal. All KPIs should hold in GREEN zone for 2+ consecutive sprints.", "Watch for regression patterns after team changes or new projects."]
        }
    ]

    # Calculate improvement trajectory
    for i, template in enumerate(plan_templates):
        sprint_num = i + 1  # Relative sprint numbering (Sprint 1, 2, 3...)
        factor = 1 - (i * 0.12)  # Progressive improvement factor

        targets = {}
        for kpi in ["SC", "RC", "SCT", "EWIP", "ECT"]:
            curr_val = prev[kpi]
            if kpi in ["SC", "RC"]:
                # Higher is better
                improvement = min(current[kpi] * 0.08 * (i + 1), 30)
                tgt = round(min(curr_val + improvement, 85 if kpi == "SC" else 75), 1)
            elif kpi == "EWIP":
                # Lower is better, integer
                reduction = min(2 + i, int(current["EWIP"] * 0.6))
                tgt = max(int(curr_val - reduction), 3)
            else:
                # Lower is better (SCT, ECT)
                tgt = round(max(curr_val * (0.92 - i * 0.04), 2.5 if kpi == "ECT" else 3), 1)

            targets[kpi] = {
                "current": round(curr_val, 1) if kpi != "EWIP" else int(curr_val),
                "target": tgt if kpi != "EWIP" else int(tgt),
                "zone_current": zone_for(kpi, curr_val),
                "zone_target": zone_for(kpi, tgt)
            }
            prev[kpi] = tgt

        sprints.append({
            "sprint_num": sprint_num,
            "theme": template["theme"],
            "targets": targets,
            "actions": template["actions"],
            "watch": template["watch"]
        })

    return sprints

def main():
    args = parse_args()
    calc_script = find_calc_script(args.calc_script)

    if not os.path.exists(calc_script):
        print(f"ERROR: calculate_kpis.py not found at {calc_script}", file=sys.stderr)
        sys.exit(1)

    data_dir = args.data_dir
    for f in ["hTask.csv", "hEpic.csv", "hInitiative.csv", "hSprints.csv"]:
        if not os.path.exists(os.path.join(data_dir, f)):
            print(f"ERROR: {f} not found in {data_dir}", file=sys.stderr)
            sys.exit(1)

    print(f"Discovering sprints for team: {args.team}...")
    sprint_names = discover_sprints(calc_script, data_dir, args.team, args.num_sprints)

    if not sprint_names:
        print(f"ERROR: No closed sprints found for team '{args.team}'", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(sprint_names)} closed sprints: {sprint_names}")

    # Calculate KPIs for each sprint
    all_kpis = []
    for sprint in sprint_names:
        print(f"  Calculating KPIs for {sprint}...")
        kpi_data = calculate_kpis_for_sprint(calc_script, data_dir, sprint)
        all_kpis.append(kpi_data)

    # Extract KPI values for trend analysis
    latest = all_kpis[-1]["kpis"]
    kpi_values = {
        "SC": [s["kpis"]["SC"]["value"] for s in all_kpis],
        "RC": [s["kpis"]["RC"]["value"] for s in all_kpis],
        "SCT": [s["kpis"]["SCT"]["value"] for s in all_kpis],
        "EWIP": [s["kpis"]["EWIP"]["value"] for s in all_kpis],
        "ECT": [s["kpis"]["ECT"]["value"] for s in all_kpis],
    }

    # Compute trends
    trends = {kpi: compute_trend(kpi, vals) for kpi, vals in kpi_values.items()}

    # Detect feedback loops
    feedback_loops = detect_feedback_loops(kpi_values)

    # Health rating
    red_count = sum(1 for k in latest if latest[k]["zone"] == "RED")
    yellow_count = sum(1 for k in latest if latest[k]["zone"] == "YELLOW")
    health = max(1, 5 - red_count - (yellow_count * 0.5))

    # Root cause analysis
    if latest["EWIP"]["zone"] == "RED":
        root_cause = "EWIP"
        root_cause_explanation = (
            f"With {int(latest['EWIP']['value'])} epics touched, the team is spread too thin. "
            "This drives context switching, inflates story cycle times, and prevents sprint completion. "
            "Reducing WIP is the highest-leverage intervention."
        )
    elif latest["SCT"]["zone"] == "RED":
        root_cause = "SCT"
        root_cause_explanation = (
            f"Average story cycle time of {latest['SCT']['value']:.1f} days is too high. "
            "Stories are not being broken down small enough, causing sprint spillover and slower epic delivery."
        )
    elif latest["SC"]["zone"] == "RED":
        root_cause = "SC"
        root_cause_explanation = (
            f"Sprint completion at {latest['SC']['value']:.1f}% indicates poor sprint planning discipline. "
            "The team is overcommitting or not protecting sprint scope from mid-sprint changes."
        )
    else:
        root_cause = "General"
        root_cause_explanation = "No single critical root cause. Focus on maintaining current performance and gradual improvement."

    # Build improvement plan
    improvement_plan = build_improvement_plan(latest, args.team)

    # Assemble output
    output = {
        "team": args.team,
        "sprints_analyzed": sprint_names,
        "date_generated": datetime.now().strftime("%Y-%m-%d"),
        "health_rating": round(health, 1),
        "root_cause": root_cause,
        "root_cause_explanation": root_cause_explanation,
        "trends": trends,
        "feedback_loops": feedback_loops,
        "sprints": all_kpis,
        "improvement_plan": improvement_plan
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults written to {args.output}")
    print(f"  Health: {health}/5")
    print(f"  Trends: {json.dumps(trends)}")
    print(f"  Feedback loops: {len(feedback_loops)}")
    print(f"  Improvement sprints: {len(improvement_plan)}")

if __name__ == "__main__":
    main()
