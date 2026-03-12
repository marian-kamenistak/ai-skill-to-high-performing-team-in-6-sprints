# To High-Performing Team in 6 Sprints

**Your team is busy. Nothing ships.**

Sprint commitments missed. Epics dragging on for months. Engineers context-switching between 6+ things. Stakeholders losing trust. Sound familiar?

This tool diagnoses why and builds you a concrete plan to fix it. Not theory, not a workshop, not a Miro board full of stickies. Data from your actual Jira, turned into 5 KPIs that tell you exactly where the problem is and what to do first.

---

## What It Does

Feed it your Jira exports. Get back:

1. **A quantified diagnosis** across 5 KPIs: Sprint Completion, Roadmap Contribution, Story Cycle Time, Epic WIP, and Epic Cycle Time
2. **Root cause identification** with cascading effects (not symptoms, actual causes)
3. **A 6-sprint improvement plan** with specific actions, targets, and watch items per sprint
4. **An interactive HTML dashboard** you can share with your team and leadership

The plan follows a proven sequence: reduce WIP first (highest leverage), then fix story breakdown, then predictability, then alignment, and finally lock in the gains.

## Real Results

Teams using this approach typically see:

| KPI | Before | After 6 Sprints | What It Means |
|-----|--------|-----------------|---------------|
| Sprint Completion | ~40% | ~80% | Team delivers what they commit to |
| Story Cycle Time | ~14 days | ~4 days | Stories are well-scoped and flow |
| Epic WIP | 6-8 active | 3 | Focused, fast value delivery |
| Roadmap Contribution | ~25% | ~55% | Work connects to strategy |
| Epic Cycle Time | ~12 weeks | ~4 weeks | Features ship in weeks, not months |

## Try It Now (Demo Data Included)

You do not need your own Jira data to see how it works. The repo includes obfuscated demo data from a real engineering organization.

```bash
# 1. List available demo teams
python3 scripts/calculate_kpis.py \
  --tasks data/demo/hTask.csv \
  --epics data/demo/hEpic.csv \
  --initiatives data/demo/hInitiative.csv \
  --sprints data/demo/hSprints.csv \
  --list-teams

# 2. Run analysis for a team (e.g., Alpha)
python3 scripts/build_improvement_plan.py \
  --team Alpha \
  --data-dir data/demo \
  --output plan_alpha.json

# 3. Generate the interactive dashboard
python3 scripts/generate_interactive_html.py \
  --json-files plan_alpha.json \
  --output alpha_report.html

# 4. Open alpha_report.html in your browser
```

## Use It on Your Own Team

### Step 1: Export from Jira

You need 4 CSV files from Jira using the [Hierarchy for Jira](https://marketplace.atlassian.com/apps/1224459) plugin. Detailed instructions are in `references/jira_export_guide.md`.

| File | Contains |
|------|----------|
| `hTask.csv` | Stories, tasks, bugs |
| `hEpic.csv` | Epics |
| `hInitiative.csv` | Initiatives |
| `hSprints.csv` | Sprint membership |

### Step 2: Run the Analysis

Same commands as above, just point to your data folder instead of `data/demo/`.

### Sprint Naming

The tool discovers teams from sprint names. Your sprints should follow this pattern:

```
{TeamName} {Year} Q{Quarter} S{SprintNumber}
```

Examples: `Platform 2025 Q1 S3`, `Backend 2026 Q2 S1`

## The 5 KPIs

| KPI | Measures | GREEN | YELLOW | RED |
|-----|----------|-------|--------|-----|
| **SC** Sprint Completion | % of sprint stories completed | >= 80% | >= 50% | < 50% |
| **RC** Roadmap Contribution | % of work tied to roadmap | >= 50% | >= 35% | < 35% |
| **SCT** Story Cycle Time | Avg days per story | <= 6 days | <= 9 days | > 9 days |
| **EWIP** Epic WIP | Active epics in sprint | <= 3 | <= 5 | > 5 |
| **ECT** Epic Cycle Time | Avg weeks per epic | <= 5 weeks | <= 8 weeks | > 8 weeks |

**Why these 5?** They form a connected system. EWIP is the highest-leverage metric. When a team touches too many epics, story cycle times go up, sprint completion drops, epic completion stalls, and roadmap alignment drifts. Fix WIP and everything else follows.

## Why This Exists

I have run 300+ coaching sessions with engineering leaders. The pattern is always the same: teams know what they should do, but navigating the human side (the PM who wants everything in parallel, the developer who resists smaller stories, the stakeholder who keeps pinging about paused work) is where they get stuck.

This tool handles the measurement and diagnosis. The hard part, the conversations and the change management, is where experienced coaching makes the difference.

**If your team is stuck and you want measurable improvement within 3 months, reach out:**

Marian Kamenistak
Engineering Leadership Coach | Fractional VP of Engineering
[LinkedIn](https://www.linkedin.com/in/mariankamenistak/) | [kamenistak.com](https://kamenistak.com)

---

## Requirements

- Python 3.8+
- pandas (`pip install pandas`)
- Jira with Hierarchy for Jira plugin (for your own data)

## License

MIT
