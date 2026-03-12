---
name: to-high-performing-team-in-6-sprints
description: >
  AI-powered sprint performance coach that transforms underperforming dev teams into high-performing ones in 6 sprints.
  Analyzes Jira CSV exports, calculates 5 engineering KPIs (Sprint Completion, Roadmap Contribution, Story Cycle Time,
  Epic WIP Count, Epic Cycle Time), detects dangerous feedback loops, and builds a personalized 6-sprint improvement plan
  with an interactive HTML report. Use this skill when the user mentions sprint evaluation, sprint review, team KPIs,
  sprint metrics, engineering productivity, sprint health check, team performance analysis, delivery metrics, improvement plan,
  or wants to boost their dev team efficiency. Also triggers on: "evaluate my team", "how did the team do this sprint",
  "sprint performance review", "calculate KPIs from Jira", "build improvement plan", "fix my team's delivery",
  "why is my team slow", "team health check", "engineering efficiency", "dev team coaching".
---

# AI Agent to High-Performing Dev Team in 6 Sprints

Transform your engineering team from low-performing to high-performing in 6 sprints using data-driven coaching.

This skill analyzes your Jira sprint data, identifies root causes of underperformance, and creates a concrete 6-sprint improvement plan your team can commit to. No guesswork, no generic advice. Just evidence-based actions tied to real KPI targets.

## How It Works (The Big Picture)

The skill follows a simple loop that mirrors how great engineering coaches work:

1. **Measure** your team's current state across 5 KPIs
2. **Diagnose** what's actually holding you back (not symptoms, root causes)
3. **Prescribe** a sequenced improvement plan (6 sprints, each with a theme)
4. **Visualize** everything in an interactive HTML report the team can rally around

The improvement plan is not random. It follows a proven priority sequence: fix WIP first (highest leverage), then story breakdown, then sprint predictability, then roadmap alignment, and finally optimize for sustained flow.

## What You Need

4 CSV files exported from Jira. The skill reads these as semicolon-delimited CSVs.

| File | What It Contains | Why We Need It |
|------|-----------------|----------------|
| `hTask.csv` | Stories, tasks, bugs | Sprint completion, story cycle times, parent epic mapping |
| `hEpic.csv` | Epics (parents of tasks) | WIP count, epic cycle times, roadmap labels |
| `hInitiative.csv` | Initiatives (parents of epics) | Quarter planning context |
| `hSprints.csv` | Sprint membership records | Which tasks were in which sprint, completion status |

Read `references/jira_export_guide.md` for step-by-step instructions on how to export these from Jira. Show this guide to the user if they ask how to get the data.

Template files with the exact column structure are in `data/templates/`. The user's CSVs need these key columns (extra columns are fine and will be ignored):

**hTask.csv critical columns:** `ID`, `Stage`, `Parent key`, `Parent name`, `Parent status`, `All Development Days Round Up`, `All Cycle Time Days`

**hEpic.csv critical columns:** `ID`, `Name`, `Stage`, `Labels`, `All Cycle Time Days`

**hInitiative.csv critical columns:** `ID`, `Stage`, `Initiative quarter`

**hSprints.csv critical columns:** `ID`, `Sprint Name`, `Is Completed in Sprint`, `Sprint State`

## Sprint Naming Convention

The skill auto-discovers teams from sprint names. Sprints should follow this pattern:

```
{TeamName} {Year} Q{Quarter} S{SprintNumber}
```

Examples: `Alpha 2025 Q1 S3`, `Backend 2026 Q2 S1`, `Platform 2025 Q4 S6`

If the user's sprint naming is different, they'll need to rename or you can help them adjust the parsing regex in `calculate_kpis.py`.

## Step-by-Step Workflow

### Step 1: Get the data

Ask the user to provide their 4 Jira CSV exports. Point them to `references/jira_export_guide.md` if they need help exporting. The files should be placed in a `data/` folder.

Verify the files exist and have the right structure:
```bash
head -1 {data}/hTask.csv
head -1 {data}/hSprints.csv
```

Check that files are semicolon-delimited and contain the required columns.

### Step 2: Discover teams

```bash
python3 {skill_path}/scripts/calculate_kpis.py \
  --tasks {data}/hTask.csv \
  --epics {data}/hEpic.csv \
  --initiatives {data}/hInitiative.csv \
  --sprints {data}/hSprints.csv \
  --list-teams
```

Present the discovered teams and let the user pick which team(s) to analyze. Use AskUserQuestion if there are multiple teams.

### Step 3: Run analysis for selected team(s)

For each team, run the orchestration script:

```bash
python3 {skill_path}/scripts/build_improvement_plan.py \
  --team {TEAM_NAME} \
  --data-dir {data} \
  --output /tmp/plan_{TEAM_NAME}.json
```

This script:
- Auto-discovers the last 4 closed sprints for the team
- Calculates all 5 KPIs per sprint
- Computes trends (improving / worsening / stable)
- Detects dangerous feedback loops (WIP Death Spiral, Delivery Stall)
- Identifies the root cause of underperformance
- Generates a health rating (1-5 stars)
- Builds a personalized 6-sprint improvement plan with concrete targets

### Step 4: Generate interactive HTML report

For a single team:
```bash
python3 {skill_path}/scripts/generate_interactive_html.py \
  --json-files /tmp/plan_{TEAM}.json \
  --output {output}/{TEAM}_improvement_plan.html
```

For multiple teams (creates a team selector):
```bash
python3 {skill_path}/scripts/generate_interactive_html.py \
  --json-files /tmp/plan_Team1.json /tmp/plan_Team2.json /tmp/plan_Team3.json \
  --output {output}/team_improvement_plans.html
```

Save the HTML to the workspace/outputs folder and provide a `computer://` link.

### Step 5: Present results to the user

After generating the report, give the user a quick executive summary:
- Team health rating (X/5 stars)
- Root cause (what's the primary bottleneck)
- Key insight (what should they focus on first)
- Link to the full interactive HTML report

Example summary format:
```
Team Alpha: 2/5 stars
Root cause: EWIP (11 epics in flight, should be 3-4)
The team is spread across too many epics, causing context switching and slow delivery.
Sprint 1 focus: Reduce WIP by setting a hard limit of 3-4 active epics.
```

## The 5 KPIs Explained

### SC (Sprint Completion %) - Predictability
Percentage of sprint tasks completed within the sprint boundary.
- GREEN: 80-100% (team delivers what they commit to)
- YELLOW: 50-79% (some spillover, needs attention)
- RED: 0-49% (severe overcommitment or scope creep)

### RC (Roadmap Contribution %) - Alignment
Percentage of sprint work that ties to planned roadmap items (quarterly-labelled epics).
- GREEN: 50-100% (well-aligned with strategy)
- YELLOW: 35-49% (drifting from roadmap)
- RED: 0-34% (mostly reactive/unplanned work)

### SCT (Story Cycle Time) - Velocity
Average development days for completed stories. Measures how long individual work items take.
- GREEN: 1-6 days (stories are well-scoped)
- YELLOW: 7-9 days (stories too large)
- RED: 10+ days (stories need better breakdown)

### EWIP (Epic WIP Count) - Focus
Number of distinct epics the team touches in a sprint. The single highest-leverage metric.
- GREEN: 1-3 epics (focused, fast delivery)
- YELLOW: 4-5 epics (starting to spread thin)
- RED: 6+ epics (context switching kills productivity)

### ECT (Epic Cycle Time) - Value Delivery
Average time from epic start to epic completion, in weeks.
- GREEN: 1-5 weeks (fast value delivery)
- YELLOW: 6-8 weeks (acceptable but improvable)
- RED: 9+ weeks (epics dragging on too long)

## Metric Relationships (Why These 5 KPIs Matter Together)

These metrics are deeply connected. When one moves, others follow:

| When this goes up | SC | RC | SCT | ECT | EWIP |
|-------------------|-----|-----|------|------|------|
| SC (completion) | -- | +35% | -30% | -50% | -20% |
| RC (alignment) | +20% | -- | +10% | -35% | -25% |
| SCT (cycle time) | -60% | -30% | -- | +70% | +40% |
| ECT (epic time) | -25% | -40% | +30% | -- | +55% |
| EWIP (wip count) | -35% | -45% | +50% | +65% | -- |

The key insight: EWIP is the most connected metric. Reducing epic WIP creates a virtuous cycle that improves everything else.

## Dangerous Feedback Loops

Watch for these self-reinforcing patterns:

**WIP Death Spiral:** EWIP goes up, which inflates SCT (+50%), which inflates ECT (+70%), which makes teams start even more epics to "show progress", driving EWIP even higher (+55%). Break this by setting hard WIP limits.

**Delivery Stall:** SCT goes up, which tanks SC (-60%), which inflates ECT, which drops RC (-40%). The team feels busy but nothing gets done. Break this by improving story breakdown.

**Virtuous Cycle (the goal):** EWIP goes down, SCT follows, SC goes up, ECT drops, RC rises. Everything improves when you reduce WIP.

## Improvement Plan Priority Sequence

The 6-sprint plan follows this evidence-based priority:

1. **Sprint 1: Reduce WIP** (highest leverage, breaks death spirals)
2. **Sprint 2: Improve Story Breakdown** (smaller stories = faster cycle times)
3. **Sprint 3: Stabilize Sprint Predictability** (build trust in commitments)
4. **Sprint 4: Strengthen Roadmap Alignment** (connect work to strategy)
5. **Sprint 5: Sustain and Optimize Flow** (make improvements permanent)
6. **Sprint 6: Continuous Improvement Culture** (share learnings, prevent regression)

## Tips for Presenting to Engineering Leaders

When sharing results with the team or their manager, frame it positively:
- This is a coaching tool, not a judgment
- The data tells us where the biggest opportunities are
- Small changes (WIP limits, story breakdown) create big improvements
- The 6-sprint plan is achievable, each sprint has just 2-3 actions
- Track progress by re-running this analysis every sprint
