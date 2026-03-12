#!/usr/bin/env python3
"""
Sprint KPI Calculator
Calculates 5 engineering efficiency KPIs for a given sprint from Jira CSV exports.
Outputs JSON to stdout for easy consumption by the skill.

Usage:
    python calculate_kpis.py \
        --tasks hTask.csv \
        --epics hEpic.csv \
        --initiatives hInitiative.csv \
        --sprints hSprints.csv \
        --sprint-name "COM 2026 Q1 S4"
"""

import pandas as pd
import numpy as np
import re
import json
import argparse
import sys

# ─── STAGE GROUPINGS ───
DONE_STAGES = {'Done', 'Closed', 'Canceled', 'Cancelled', 'Resolved', 'In Acceptance', 'Acceptance'}
IN_DEV_STAGES = {'In Progress', 'in progress', 'In construction', 'In review', 'In test',
                  'Testing in progress', 'Testing finished', 'Delivery', 'Deliver', 'READY TO TEST'}
UNUSED_STAGES = {'New', 'ABANDONED', 'Backlog', 'CAPTURE', 'Capture', 'Planned', 'NEW',
                 'Not Started', 'Parking lot', 'To Do', 'abandoned', 'capture'}

THRESHOLDS = {
    'SC': {'green': 80, 'yellow': 50},
    'RC': {'green': 50, 'yellow': 35},
    'SCT': {'green': 6, 'yellow': 9},
    'EWIP': {'green': 3, 'yellow': 5},
    'ECT': {'green': 5, 'yellow': 8},
}


def zone(metric, value):
    """Determine RED/YELLOW/GREEN zone for a KPI value."""
    t = THRESHOLDS[metric]
    if metric in ('SC', 'RC'):
        # Higher is better
        if value >= t['green']:
            return 'GREEN'
        elif value >= t['yellow']:
            return 'YELLOW'
        else:
            return 'RED'
    else:
        # Lower is better (SCT, EWIP, ECT)
        if value <= t['green']:
            return 'GREEN'
        elif value <= t['yellow']:
            return 'YELLOW'
        else:
            return 'RED'


def calculate_kpis(tasks_path, epics_path, initiatives_path, sprints_path, sprint_name):
    """Calculate all 5 KPIs for a given sprint. Returns a dict."""

    # Load data
    tasks = pd.read_csv(tasks_path, sep=';', low_memory=False)
    epics = pd.read_csv(epics_path, sep=';', low_memory=False)
    initiatives = pd.read_csv(initiatives_path, sep=';', low_memory=False)
    sprint_data = pd.read_csv(sprints_path, sep=';', low_memory=False)

    # Filter to target sprint
    sprint_tasks = sprint_data[sprint_data['Sprint Name'] == sprint_name].copy()
    sprint_task_ids = set(sprint_tasks['ID'].unique())
    com_tasks = tasks[tasks['ID'].isin(sprint_task_ids)].copy()

    if len(com_tasks) == 0:
        return {'error': f'No tasks found for sprint: {sprint_name}', 'sprint': sprint_name}

    # Completed in sprint from hSprints
    completed_in_sprint_ids = set(
        sprint_tasks[sprint_tasks['Is Completed in Sprint'] == 'Y']['ID'].unique()
    )

    # Currently done (includes spillover)
    now_done_ids = set(com_tasks[com_tasks['Stage'].isin(DONE_STAGES)]['ID'])

    result = {
        'sprint': sprint_name,
        'total_tasks': len(com_tasks),
        'completed_in_sprint': len(completed_in_sprint_ids),
        'currently_done': len(now_done_ids),
        'spillover': len(now_done_ids - completed_in_sprint_ids),
        'kpis': {}
    }

    # ═══ KPI 1: SC (Sprint Completion %) ═══
    total = len(com_tasks)
    completed = len(completed_in_sprint_ids)
    sc = (completed / total) * 100 if total > 0 else 0

    result['kpis']['SC'] = {
        'value': round(sc, 1),
        'unit': '%',
        'zone': zone('SC', sc),
        'completed': completed,
        'total': total,
        'spillover': len(now_done_ids - completed_in_sprint_ids),
        'not_completed': total - len(now_done_ids)
    }

    # ═══ KPI 2: RC (Roadmap Contribution %) ═══
    # Join tasks to epic Labels via Parent key
    parent_keys = com_tasks['Parent key'].dropna().unique()
    epic_labels = epics[epics['ID'].isin(parent_keys)][['ID', 'Labels', 'Stage']].copy()
    epic_labels_dict = dict(zip(epic_labels['ID'], epic_labels['Labels']))
    epic_stage_dict = dict(zip(epic_labels['ID'], epic_labels['Stage']))

    quarterly_pattern = re.compile(r'\d{2}Q[1-4]')

    roadmap_count = 0
    roadmap_stretched_count = 0
    epic_backlog_count = 0
    orphan_count = 0

    for _, task in com_tasks.iterrows():
        parent = task.get('Parent key')
        if pd.isna(parent) or str(parent).strip() == '':
            orphan_count += 1
            continue

        labels = epic_labels_dict.get(parent, '')
        epic_stage = epic_stage_dict.get(parent, '')

        if pd.notna(labels) and quarterly_pattern.search(str(labels)):
            roadmap_count += 1
        elif epic_stage in IN_DEV_STAGES or epic_stage == 'In Progress':
            roadmap_stretched_count += 1
        else:
            epic_backlog_count += 1

    rc_strict = (roadmap_count / total) * 100 if total > 0 else 0
    rc_combined = ((roadmap_count + roadmap_stretched_count) / total) * 100 if total > 0 else 0

    result['kpis']['RC'] = {
        'value': round(rc_combined, 1),
        'value_strict': round(rc_strict, 1),
        'unit': '%',
        'zone': zone('RC', rc_combined),
        'breakdown': {
            'roadmap': roadmap_count,
            'roadmap_pct': round(roadmap_count / total * 100, 1) if total > 0 else 0,
            'roadmap_stretched': roadmap_stretched_count,
            'roadmap_stretched_pct': round(roadmap_stretched_count / total * 100, 1) if total > 0 else 0,
            'epic_backlog': epic_backlog_count,
            'epic_backlog_pct': round(epic_backlog_count / total * 100, 1) if total > 0 else 0,
            'orphan': orphan_count,
            'orphan_pct': round(orphan_count / total * 100, 1) if total > 0 else 0,
        }
    }

    # ═══ KPI 3: SCT (Story Cycle Time / Sprint Dev Days) ═══
    completed_tasks = com_tasks[com_tasks['ID'].isin(completed_in_sprint_ids)].copy()
    completed_tasks['dev_days'] = pd.to_numeric(
        completed_tasks['All Development Days Round Up'], errors='coerce'
    )
    dev_data = completed_tasks[completed_tasks['dev_days'].notna() & (completed_tasks['dev_days'] > 0)]

    if len(dev_data) > 0:
        sct_avg = float(dev_data['dev_days'].mean())
        sct_median = float(dev_data['dev_days'].median())

        # Distribution buckets
        bins = [0, 1, 3, 5, 7, 10, 15, 20, 50, 200]
        labels_list = ['0-1d', '1-3d', '3-5d', '5-7d', '7-10d', '10-15d', '15-20d', '20-50d', '50d+']
        distribution = {}
        for i in range(len(bins) - 1):
            count = int(((dev_data['dev_days'] > bins[i]) & (dev_data['dev_days'] <= bins[i+1])).sum())
            if count > 0:
                distribution[labels_list[i]] = count
    else:
        sct_avg = 0
        sct_median = 0
        distribution = {}

    result['kpis']['SCT'] = {
        'value': round(sct_avg, 1),
        'median': round(sct_median, 1),
        'unit': 'days',
        'zone': zone('SCT', sct_avg),
        'tasks_with_data': len(dev_data),
        'distribution': distribution
    }

    # ═══ KPI 4: EWIP (Epic WIP Count) ═══
    parent_status = com_tasks[com_tasks['Parent key'].notna()].groupby('Parent key').agg({
        'Parent status': 'first',
        'Parent name': 'first',
        'ID': 'count'
    }).rename(columns={'ID': 'task_count'})

    in_progress_epics = parent_status[
        ~parent_status['Parent status'].isin(DONE_STAGES) &
        ~parent_status['Parent status'].isin(UNUSED_STAGES)
    ]
    backlog_epics = parent_status[parent_status['Parent status'].isin(UNUSED_STAGES)]
    done_epics = parent_status[parent_status['Parent status'].isin(DONE_STAGES)]

    ewip = len(parent_status)  # Total distinct epics touched
    ewip_active = len(in_progress_epics)

    epic_details = []
    for epic_key, row in parent_status.iterrows():
        epic_details.append({
            'key': str(epic_key),
            'name': str(row['Parent name'])[:80],
            'status': str(row['Parent status']),
            'task_count': int(row['task_count'])
        })

    result['kpis']['EWIP'] = {
        'value': ewip,
        'value_active_only': ewip_active,
        'unit': 'epics',
        'zone': zone('EWIP', ewip),
        'zone_active_only': zone('EWIP', ewip_active),
        'breakdown': {
            'in_progress': ewip_active,
            'backlog': len(backlog_epics),
            'done': len(done_epics)
        },
        'epics': sorted(epic_details, key=lambda x: x['task_count'], reverse=True)
    }

    # ═══ KPI 5: ECT (Epic Cycle Time in weeks) ═══
    sprint_epic_ids = com_tasks['Parent key'].dropna().unique()
    sprint_epics = epics[epics['ID'].isin(sprint_epic_ids)].copy()
    sprint_epics['ct_days'] = pd.to_numeric(sprint_epics['All Cycle Time Days'], errors='coerce')

    epics_with_ct = sprint_epics[sprint_epics['ct_days'].notna() & (sprint_epics['ct_days'] > 0)]

    if len(epics_with_ct) > 0:
        ect_days = float(epics_with_ct['ct_days'].mean())
        ect_weeks = ect_days / 7
        ect_median_days = float(epics_with_ct['ct_days'].median())
        ect_median_weeks = ect_median_days / 7

        epic_ct_details = []
        for _, row in epics_with_ct.sort_values('ct_days', ascending=False).head(15).iterrows():
            epic_ct_details.append({
                'key': str(row['ID']),
                'name': str(row['Name'])[:80],
                'ct_days': round(float(row['ct_days']), 1),
                'ct_weeks': round(float(row['ct_days']) / 7, 1),
                'stage': str(row['Stage'])
            })
    else:
        ect_weeks = 0
        ect_median_weeks = 0
        epic_ct_details = []

    result['kpis']['ECT'] = {
        'value': round(ect_weeks, 1),
        'value_days': round(ect_days, 1) if len(epics_with_ct) > 0 else 0,
        'median_weeks': round(ect_median_weeks, 1) if len(epics_with_ct) > 0 else 0,
        'unit': 'weeks',
        'zone': zone('ECT', ect_weeks),
        'epics_with_data': len(epics_with_ct),
        'epics': epic_ct_details
    }

    return result


def list_teams(sprints_path):
    """Extract available team names from sprint naming conventions."""
    sprint_data = pd.read_csv(sprints_path, sep=';', low_memory=False)
    sprint_names = sprint_data['Sprint Name'].dropna().unique()

    teams = set()
    for name in sprint_names:
        match = re.match(r'^(.+?)\s+\d{4}\s+Q\d+\s+S\d+', str(name))
        if match:
            teams.add(match.group(1).strip())

    return sorted(teams)


def find_sprints(sprints_path, team_prefix, last_n=4):
    """Find the last N completed sprints for a team."""
    sprint_data = pd.read_csv(sprints_path, sep=';', low_memory=False)

    # Get unique sprint names matching the team prefix
    pattern = re.compile(rf'^{re.escape(team_prefix)}\s+(\d{{4}})\s+Q(\d+)\s+S(\d+)$')

    sprint_info = []
    for name in sprint_data['Sprint Name'].dropna().unique():
        match = pattern.match(str(name))
        if match:
            year, quarter, sprint_num = int(match.group(1)), int(match.group(2)), int(match.group(3))
            # Check if sprint has any closed state
            states = sprint_data[sprint_data['Sprint Name'] == name]['Sprint State'].unique()
            sprint_info.append({
                'name': name,
                'year': year,
                'quarter': quarter,
                'sprint': sprint_num,
                'states': list(states),
                'sort_key': year * 100 + quarter * 10 + sprint_num
            })

    # Filter to only closed sprints, sort descending, take last N
    closed_sprints = [s for s in sprint_info if 'closed' in s['states']]
    closed_sprints.sort(key=lambda x: x['sort_key'], reverse=True)
    return [s['name'] for s in closed_sprints[:last_n]]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sprint KPI Calculator')
    parser.add_argument('--tasks', required=True, help='Path to hTask.csv')
    parser.add_argument('--epics', required=True, help='Path to hEpic.csv')
    parser.add_argument('--initiatives', required=True, help='Path to hInitiative.csv')
    parser.add_argument('--sprints', required=True, help='Path to hSprints.csv')
    parser.add_argument('--sprint-name', help='Sprint name to evaluate')
    parser.add_argument('--list-teams', action='store_true', help='List available teams')
    parser.add_argument('--find-sprints', help='Find last sprints for a team prefix')
    parser.add_argument('--last-n', type=int, default=4, help='Number of sprints to find (default: 4)')

    args = parser.parse_args()

    if args.list_teams:
        teams = list_teams(args.sprints)
        print(json.dumps({'teams': teams}, indent=2))
    elif args.find_sprints:
        sprint_names = find_sprints(args.sprints, args.find_sprints, args.last_n)
        print(json.dumps({'team': args.find_sprints, 'sprints': sprint_names}, indent=2))
    elif args.sprint_name:
        result = calculate_kpis(
            args.tasks, args.epics, args.initiatives, args.sprints, args.sprint_name
        )
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()
        sys.exit(1)
