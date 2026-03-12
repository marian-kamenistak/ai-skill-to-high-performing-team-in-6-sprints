# How to Export Your Jira Data

This guide walks you through exporting the 4 CSV files needed for the sprint performance analysis. The export uses Jira's built-in Hierarchy for Jira (or similar portfolio/structure plugin) export functionality.

## Prerequisites

- Access to your Jira instance with at least read permissions on the project(s) you want to analyze
- A Jira plugin that supports hierarchical CSV export (e.g., Hierarchy for Jira, Structure, BigPicture, or Advanced Roadmaps export)
- The team(s) you want to analyze should use sprints with a consistent naming convention: `{TeamName} {Year} Q{Quarter} S{SprintNumber}`

## Export Method: Hierarchy for Jira Plugin

If you use the Hierarchy for Jira plugin, follow these steps:

### Export 1: hTask.csv (Stories, Tasks, Bugs)

1. Go to your Jira project board or backlog
2. Open the Hierarchy for Jira view (or the board's export function)
3. Filter to Level 1 items (Stories, Tasks, Bugs, Sub-tasks)
4. Select these columns for export:
   - `ID` (Jira issue key, e.g., PROJ-123)
   - `Name` (issue summary)
   - `Type` (Story, Bug, Task, etc.)
   - `Stage` (current workflow status)
   - `Priority`
   - `Labels`
   - `Parent key` (the epic this task belongs to)
   - `Parent name`
   - `Parent type`
   - `Parent status`
   - `Assignee name`
   - `Sprints` (sprint membership)
   - `All Development Days Round Up` (days the task spent in development stages)
   - `All Cycle Time Days` (total cycle time from start to done)
   - `Team Name`
   - `Level Name` (should be "L1 - Sprints" or similar)
   - `Is Completed`
   - `CreatedDate`
5. Export as CSV with semicolon delimiter
6. Save as `hTask.csv`

### Export 2: hEpic.csv (Epics)

1. Same view, filter to Level 2 items (Epics)
2. Select these columns:
   - `ID`
   - `Name`
   - `Type`
   - `Stage`
   - `Priority`
   - `Labels` (this is critical: quarterly labels like "25Q1" mark roadmap items)
   - `All Cycle Time Days`
   - `Initiative key` (parent initiative)
   - `Team Name`
   - `Level Name` (should be "L2 - Epics")
   - `Is Completed`
3. Export as semicolon-delimited CSV
4. Save as `hEpic.csv`

### Export 3: hInitiative.csv (Initiatives)

1. Filter to Level 3 items (Initiatives)
2. Select these columns:
   - `ID`
   - `Name`
   - `Type`
   - `Stage`
   - `Priority`
   - `Initiative quarter` (e.g., "Q1 2025")
   - `Team Name`
   - `Level Name` (should be "L3 - Initiatives")
3. Export as semicolon-delimited CSV
4. Save as `hInitiative.csv`

### Export 4: hSprints.csv (Sprint Membership)

This export is different from the others. It contains one row per task-sprint combination.

1. Export sprint membership data with these columns:
   - `ID` (task issue key)
   - `Sprint Name` (e.g., "Team1 2025 Q1 S3")
   - `Is Completed in Sprint` (Y/N: was this task completed within this sprint?)
   - `Sprint State` (active, closed, future)
2. Export as semicolon-delimited CSV
3. Save as `hSprints.csv`

## Alternative: Manual Export from Jira

If you don't have a hierarchy plugin, you can construct these CSVs from standard Jira exports:

### Using JQL + Jira's built-in export

**For hTask.csv:**
```
project = "PROJ" AND issuetype in (Story, Bug, Task, Sub-task) ORDER BY created DESC
```
Export with relevant fields, then add the parent epic information using a VLOOKUP or script.

**For hEpic.csv:**
```
project = "PROJ" AND issuetype = Epic ORDER BY created DESC
```

**For hInitiative.csv:**
```
project = "PROJ" AND issuetype = Initiative ORDER BY created DESC
```

**For hSprints.csv:**
This one is trickier without a plugin. You need to extract sprint membership from the "Sprint" field, which Jira exports as a JSON-like string. A Python script can help parse this.

## Validation Checklist

After exporting, verify your files:

- [ ] All 4 files exist: hTask.csv, hEpic.csv, hInitiative.csv, hSprints.csv
- [ ] Files are semicolon-delimited (not comma)
- [ ] hTask.csv has `Parent key` column populated (tasks linked to epics)
- [ ] hEpic.csv has `Labels` column (for roadmap contribution tracking)
- [ ] hSprints.csv has `Sprint State` column with "closed" values (the skill only analyzes closed sprints)
- [ ] Sprint names follow the pattern: `{Team} {Year} Q{Quarter} S{Number}`
- [ ] `Is Completed in Sprint` column has Y/N values

## Common Issues

**"No teams found"**: Sprint names don't match the expected pattern. Check that your sprints use the `Team Year QX SY` naming.

**"No closed sprints"**: Only closed sprints are analyzed. Make sure your sprint admin has properly closed past sprints in Jira.

**"0% Roadmap Contribution"**: Epic labels need quarterly tags (like "25Q1", "24Q4") to be recognized as roadmap items. Ask your product owner to label epics with the relevant quarter.

**Missing cycle time data**: The `All Development Days Round Up` and `All Cycle Time Days` columns come from Jira workflow time tracking. If these are empty, your Jira workflow might not track stage transitions. Contact your Jira admin.
