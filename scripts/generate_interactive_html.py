#!/usr/bin/env python3
"""
Generate a single interactive HTML file with team selector.
Embeds pre-computed JSON for all teams. User picks a team, sees the full report.

Usage:
  python generate_interactive_html.py --data-dir ./data --output interactive_report.html
  python generate_interactive_html.py --json-files plan_Atom.json plan_COM.json --output interactive_report.html
"""

import json, argparse, sys, os, glob, subprocess
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description="Generate interactive HTML with team selector")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--json-files", nargs="+", help="Pre-computed JSON files from build_improvement_plan.py")
    group.add_argument("--data-dir", help="Data directory with CSVs. Will run build_improvement_plan.py for all teams.")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    parser.add_argument("--calc-script", default=None, help="Path to calculate_kpis.py")
    parser.add_argument("--build-script", default=None, help="Path to build_improvement_plan.py")
    return parser.parse_args()

def find_script(name, explicit_path):
    if explicit_path:
        return explicit_path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, name)

def discover_teams(calc_script, data_dir):
    result = subprocess.run(
        ["python3", calc_script,
         "--tasks", os.path.join(data_dir, "hTask.csv"),
         "--epics", os.path.join(data_dir, "hEpic.csv"),
         "--initiatives", os.path.join(data_dir, "hInitiative.csv"),
         "--sprints", os.path.join(data_dir, "hSprints.csv"),
         "--list-teams"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR listing teams: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(result.stdout)
    return data.get("teams", [])

def build_team_data(build_script, data_dir, team):
    import tempfile
    out_file = tempfile.mktemp(suffix=".json")
    result = subprocess.run(
        ["python3", build_script, "--team", team, "--data-dir", data_dir, "--output", out_file],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"WARNING: Failed for team {team}: {result.stderr}", file=sys.stderr)
        return None
    with open(out_file) as f:
        data = json.load(f)
    os.unlink(out_file)
    return data


CSS = """
  :root {
    --dark-blue: #1F4E79; --med-blue: #2E75B6; --light-blue: #D5E8F0;
    --green: #27AE60; --green-bg: #C6EFCE; --yellow: #F39C12; --yellow-bg: #FFEB9C;
    --red: #E74C3C; --red-bg: #FFC7CE;
    --gray-100: #F8F9FA; --gray-200: #E9ECEF; --gray-300: #DEE2E6;
    --gray-500: #6C757D; --gray-700: #495057; --gray-900: #212529;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--gray-100); color: var(--gray-900); line-height: 1.6; }

  /* Team Selector */
  .selector-screen { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; background: linear-gradient(135deg, var(--dark-blue) 0%, var(--med-blue) 100%); color: white; padding: 60px 40px 80px; overflow-y: auto; }
  .selector-screen h1 { font-size: 42px; font-weight: 700; margin-bottom: 8px; }
  .selector-screen .subtitle { font-size: 20px; font-weight: 300; opacity: 0.85; margin-bottom: 48px; }
  .team-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; max-width: 900px; width: 100%; }
  .team-btn { background: rgba(255,255,255,0.12); border: 2px solid rgba(255,255,255,0.25); border-radius: 12px; padding: 24px 20px; text-align: center; cursor: pointer; transition: all 0.2s; color: white; font-size: 18px; font-weight: 600; position: relative; z-index: 1; }
  .team-btn:hover { background: rgba(255,255,255,0.25); border-color: rgba(255,255,255,0.5); transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.2); }
  .team-btn:active { transform: translateY(0); }
  .team-btn .health-badge { display: inline-block; margin-top: 8px; font-size: 13px; font-weight: 400; opacity: 0.8; }
  .team-btn .health-stars { color: var(--yellow); font-size: 14px; }
  .team-btn .health-stars-empty { color: rgba(255,255,255,0.3); font-size: 14px; }
  @media (max-width: 700px) { .team-grid { grid-template-columns: repeat(2, 1fr); } }

  /* Back button */
  .back-btn { position: fixed; top: 16px; left: 16px; z-index: 100; background: var(--dark-blue); color: white; border: none; border-radius: 8px; padding: 10px 18px; font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.2); transition: all 0.2s; }
  .back-btn:hover { background: var(--med-blue); transform: translateY(-1px); }

  /* Report sections (same as before) */
  .cover { background: linear-gradient(135deg, var(--dark-blue) 0%, var(--med-blue) 100%); color: white; padding: 80px 60px; min-height: 45vh; display: flex; flex-direction: column; justify-content: center; }
  .cover h1 { font-size: 42px; font-weight: 700; margin-bottom: 8px; }
  .cover .subtitle { font-size: 22px; font-weight: 300; opacity: 0.85; margin-bottom: 32px; }
  .cover .meta { font-size: 14px; opacity: 0.6; }
  .cover .meta span { margin-right: 24px; }
  .container { max-width: 1200px; margin: 0 auto; padding: 0 40px; }
  section { padding: 48px 0; }
  section + section { border-top: 1px solid var(--gray-300); }
  h2 { font-size: 26px; font-weight: 700; color: var(--dark-blue); margin-bottom: 24px; }
  h3 { font-size: 18px; font-weight: 600; color: var(--med-blue); margin-bottom: 12px; }
  p { margin-bottom: 12px; color: var(--gray-700); }
  .health-row { display: flex; gap: 32px; align-items: stretch; margin-bottom: 32px; flex-wrap: wrap; }
  .health-card { background: white; border-radius: 12px; padding: 28px 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); flex: 1; min-width: 280px; }
  .health-card .label { font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: var(--gray-500); margin-bottom: 8px; }
  .health-card .value { font-size: 36px; font-weight: 700; color: var(--dark-blue); }
  .health-card .value .stars { color: var(--yellow); }
  .health-card .value .stars-empty { color: var(--gray-300); }
  .health-card .detail { font-size: 14px; color: var(--gray-500); margin-top: 8px; }
  .health-card.alert { border-left: 4px solid var(--red); }
  .health-card.warn { border-left: 4px solid var(--yellow); }
  .health-card.ok { border-left: 4px solid var(--green); }
  .kpi-table { width: 100%; border-collapse: separate; border-spacing: 0; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .kpi-table th { background: var(--med-blue); color: white; padding: 14px 16px; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; text-align: center; }
  .kpi-table th:first-child, .kpi-table th:nth-child(2) { text-align: left; }
  .kpi-table td { padding: 14px 16px; text-align: center; font-size: 14px; border-bottom: 1px solid var(--gray-200); }
  .kpi-table td:first-child { font-weight: 700; text-align: left; color: var(--dark-blue); }
  .kpi-table td:nth-child(2) { text-align: left; color: var(--gray-500); font-size: 13px; }
  .kpi-table tr:last-child td { border-bottom: none; }
  .zone-green { background: var(--green-bg); color: #1E7E34; font-weight: 600; }
  .zone-yellow { background: var(--yellow-bg); color: #856404; font-weight: 600; }
  .zone-red { background: var(--red-bg); color: #A71D2A; font-weight: 600; }
  .trend-good { color: var(--green); } .trend-bad { color: var(--red); } .trend-stable { color: var(--gray-500); }
  .trend-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }
  .trend-card { background: white; border-radius: 10px; padding: 20px 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
  .trend-card .kpi-name { font-weight: 700; color: var(--dark-blue); font-size: 15px; margin-bottom: 4px; }
  .trend-card .kpi-move { font-size: 13px; color: var(--gray-500); }
  .feedback-loop { background: #FFF3CD; border: 1px solid #FFEAA7; border-radius: 10px; padding: 20px 24px; margin-top: 24px; }
  .feedback-loop .fl-title { font-weight: 700; color: #856404; font-size: 15px; margin-bottom: 6px; }
  .feedback-loop .fl-body { font-size: 14px; color: #664D03; }
  .timeline-section { padding: 48px 0; }
  .timeline-wrapper { overflow-x: auto; padding: 20px 0 32px 0; -webkit-overflow-scrolling: touch; }
  .timeline { display: flex; align-items: flex-start; min-width: max-content; position: relative; padding: 0 20px; }
  .timeline::before { content: ''; position: absolute; top: 48px; left: 40px; right: 40px; height: 4px; background: linear-gradient(90deg, var(--red) 0%, var(--yellow) 40%, var(--green) 100%); border-radius: 2px; z-index: 0; }
  .timeline-node { display: flex; flex-direction: column; align-items: center; width: 220px; flex-shrink: 0; position: relative; z-index: 1; }
  .timeline-node .sprint-label { font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--gray-500); font-weight: 600; margin-bottom: 8px; }
  .timeline-node .theme-label { font-size: 14px; font-weight: 700; color: var(--dark-blue); text-align: center; margin-bottom: 12px; min-height: 40px; display: flex; align-items: center; justify-content: center; line-height: 1.3; }
  .timeline-dot { width: 24px; height: 24px; border-radius: 50%; border: 4px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.15); margin-bottom: 16px; }
  .dot-red { background: var(--red); } .dot-yellow { background: var(--yellow); } .dot-green { background: var(--green); }
  .timeline-card { background: white; border-radius: 10px; padding: 16px; width: 200px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-top: 3px solid var(--med-blue); }
  .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 12px; border-bottom: 1px solid var(--gray-200); }
  .metric-row:last-child { border-bottom: none; }
  .metric-row .m-label { font-weight: 600; color: var(--gray-700); }
  .metric-row .m-value { font-weight: 700; }
  .metric-row .m-arrow { font-size: 10px; color: var(--gray-500); margin: 0 3px; }
  .m-green { color: var(--green); } .m-yellow { color: #B8860B; } .m-red { color: var(--red); }
  .timeline-actions { margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--gray-200); }
  .timeline-actions .action-item { font-size: 11px; color: var(--gray-700); padding: 3px 0; line-height: 1.4; }
  .timeline-actions .action-item::before { content: '>'; color: var(--med-blue); font-weight: 700; margin-right: 4px; }
  .scroll-hint { text-align: center; font-size: 12px; color: var(--gray-500); margin-top: 8px; }
  .sprint-detail { background: white; border-radius: 10px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); margin-bottom: 16px; }
  .sprint-detail h3 { margin-bottom: 8px; }
  .sprint-detail .stats { font-size: 13px; color: var(--gray-500); margin-bottom: 12px; }
  .kpi-pills { display: flex; gap: 8px; flex-wrap: wrap; }
  .kpi-pill { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }
  .pill-green { background: var(--green-bg); color: #1E7E34; }
  .pill-yellow { background: var(--yellow-bg); color: #856404; }
  .pill-red { background: var(--red-bg); color: #A71D2A; }
  .footer { text-align: center; padding: 32px 40px; font-size: 12px; color: var(--gray-500); border-top: 1px solid var(--gray-300); }

  .logo { height: 48px; width: auto; margin-bottom: 28px; filter: brightness(0) invert(1); }
  .logo-report { height: 40px; width: auto; max-width: 200px; margin-bottom: 20px; filter: brightness(0) invert(1); align-self: flex-start; object-fit: contain; }

  #report-view { display: none; }
  #selector-view { display: flex; }

  @media print {
    .selector-screen { display: none !important; }
    .back-btn { display: none !important; }
    #report-view { display: block !important; }
    .cover { min-height: auto; padding: 40px; page-break-after: always; }
    section { page-break-inside: avoid; }
    .timeline-wrapper { overflow: visible; }
    .timeline { flex-wrap: wrap; min-width: auto; }
    .timeline::before { display: none; }
    body { background: white; }
  }
"""


JAVASCRIPT = """
const TEAMS = __TEAMS_JSON__;
const KPI_LABELS = {SC: 'Sprint Completion', RC: 'Roadmap Contribution', SCT: 'Story Cycle Time', EWIP: 'Epic WIP Count', ECT: 'Epic Cycle Time'};

function fmtVal(kpi, value) {
  if (kpi === 'EWIP') return Math.round(value).toString();
  if (kpi === 'SC' || kpi === 'RC') return value.toFixed(1) + '%';
  if (kpi === 'SCT') return value.toFixed(1) + 'd';
  if (kpi === 'ECT') return value.toFixed(1) + 'w';
  return String(value);
}

function zoneFor(kpi, value) {
  const t = {
    SC: [[80,100,'GREEN'],[50,79.99,'YELLOW'],[0,49.99,'RED']],
    RC: [[50,100,'GREEN'],[35,49.99,'YELLOW'],[0,34.99,'RED']],
    SCT: [[0,6.99,'GREEN'],[7,9.99,'YELLOW'],[10,9999,'RED']],
    EWIP: [[0,3.99,'GREEN'],[4,5.99,'YELLOW'],[6,9999,'RED']],
    ECT: [[0,5.99,'GREEN'],[6,8.99,'YELLOW'],[9,9999,'RED']]
  };
  for (const [lo, hi, z] of t[kpi]) { if (value >= lo && value <= hi) return z; }
  return 'RED';
}

function starsHtml(health) {
  const filled = Math.round(health);
  return '<span class="stars">' + '\\u2605'.repeat(filled) + '</span>' +
         '<span class="stars-empty">' + '\\u2605'.repeat(5 - filled) + '</span>';
}

function trendHtml(kpi, trend) {
  const higherBetter = (kpi === 'SC' || kpi === 'RC');
  if (trend === 'improving') return '<span class="trend-good">' + (higherBetter ? '\\u25B2' : '\\u25BC') + ' improving</span>';
  if (trend === 'worsening') return '<span class="trend-bad">' + (higherBetter ? '\\u25BC' : '\\u25B2') + ' worsening</span>';
  return '<span class="trend-stable">~ stable</span>';
}

function dotClass(idx, total) {
  const ratio = idx / Math.max(total - 1, 1);
  if (ratio < 0.35) return 'dot-red';
  if (ratio < 0.65) return 'dot-yellow';
  return 'dot-green';
}

function showTeam(teamName) {
  const data = TEAMS[teamName];
  if (!data) return;

  const sprints = data.sprints_analyzed;
  const shortLabels = sprints.map(s => { const m = s.match(/S(\\d+)/); return m ? 'S' + m[1] : s.slice(-5); });
  const latest = data.sprints[data.sprints.length - 1].kpis;
  const health = data.health_rating;
  const rootCause = data.root_cause;
  const rootExpl = data.root_cause_explanation;
  const trends = data.trends;
  const loops = data.feedback_loops;
  const plan = data.improvement_plan;
  const dateGen = data.date_generated;

  const kpis = ['SC', 'RC', 'SCT', 'EWIP', 'ECT'];
  const redKpis = kpis.filter(k => latest[k].zone === 'RED');
  const yellowKpis = kpis.filter(k => latest[k].zone === 'YELLOW');
  const greenKpis = kpis.filter(k => latest[k].zone === 'GREEN');

  let healthSummary = '';
  if (redKpis.length) healthSummary += redKpis.length + ' KPIs in RED zone (' + redKpis.join(', ') + '). ';
  if (yellowKpis.length) healthSummary += yellowKpis.length + ' in YELLOW (' + yellowKpis.join(', ') + '). ';
  if (greenKpis.length) healthSummary += greenKpis.length + ' healthy (' + greenKpis.join(', ') + ').';

  const healthClass = health <= 2.5 ? 'alert' : (health <= 3.5 ? 'warn' : 'ok');
  const focusClass = ['EWIP','SCT','SC'].includes(rootCause) ? 'alert' : 'warn';

  let html = '';

  // Cover
  html += '<div class="cover"><h1>' + teamName + ' Team</h1>';
  html += '<div class="subtitle">Sprint Performance Review & Improvement Plan</div>';
  html += '<div class="meta"><span>Sprints ' + shortLabels[0] + ' through ' + shortLabels[shortLabels.length-1] + '</span>';
  html += '<span>Generated ' + dateGen + '</span></div></div>';

  // Executive Summary
  html += '<div class="container"><section><h2>Executive Summary</h2>';
  html += '<div class="health-row">';
  html += '<div class="health-card ' + healthClass + '"><div class="label">Overall Health</div>';
  html += '<div class="value">' + Math.round(health) + '/5 ' + starsHtml(health) + '</div>';
  html += '<div class="detail">' + healthSummary + '</div></div>';
  html += '<div class="health-card ' + focusClass + '"><div class="label">Primary Focus</div>';
  html += '<div class="value" style="font-size:22px;line-height:1.4;">Fix ' + rootCause + '</div>';
  html += '<div class="detail">' + rootExpl.substring(0, 200) + '</div></div>';
  html += '</div></section>';

  // KPI Dashboard
  html += '<section><h2>KPI Dashboard</h2><table class="kpi-table"><thead><tr><th>KPI</th><th>Metric</th>';
  shortLabels.forEach(sl => { html += '<th>' + sl + '</th>'; });
  html += '<th>Trend</th></tr></thead><tbody>';

  kpis.forEach(kpi => {
    html += '<tr><td>' + kpi + '</td><td>' + KPI_LABELS[kpi] + '</td>';
    data.sprints.forEach(sd => {
      const v = sd.kpis[kpi].value;
      const z = sd.kpis[kpi].zone.toLowerCase();
      html += '<td class="zone-' + z + '">' + fmtVal(kpi, v) + '</td>';
    });
    html += '<td>' + trendHtml(kpi, trends[kpi]) + '</td></tr>';
  });
  html += '</tbody></table></section>';

  // Trend Analysis
  html += '<section><h2>Trend Analysis</h2><div class="trend-cards">';
  kpis.forEach(kpi => {
    const vals = data.sprints.map(s => s.kpis[kpi].value);
    const valStr = vals.map(v => fmtVal(kpi, v)).join(' \\u2192 ');
    html += '<div class="trend-card"><div class="kpi-name">' + kpi + ' (' + KPI_LABELS[kpi] + ')</div>';
    html += '<div class="kpi-move">' + valStr + '</div>';
    html += '<p style="margin-top:8px;font-size:13px;">Trend: ' + trends[kpi] + '. Latest value ' + fmtVal(kpi, vals[vals.length-1]) + ' is in ' + latest[kpi].zone + ' zone.</p></div>';
  });
  html += '</div>';

  loops.forEach(loop => {
    html += '<div class="feedback-loop"><div class="fl-title">\\u26A0 ' + loop.name + ' Detected</div>';
    html += '<div class="fl-body">' + loop.evidence + '. Pattern: ' + loop.pattern + '.</div></div>';
  });
  html += '</section>';

  // Timeline
  html += '<section class="timeline-section"><h2>Improvement Plan</h2>';
  html += '<p>' + plan.length + '-sprint journey to improve all 5 KPIs toward GREEN zone.</p>';
  html += '<div class="timeline-wrapper"><div class="timeline">';

  plan.forEach((sp, idx) => {
    const dc = dotClass(idx, plan.length);
    let theme = sp.theme;
    const parts = theme.split(' - ');
    let themeDisplay = parts.length > 1 ? parts.join('<br/>') : theme;
    if (themeDisplay.length > 30 && !themeDisplay.includes('<br/>')) {
      const words = themeDisplay.split(' ');
      const mid = Math.floor(words.length / 2);
      themeDisplay = words.slice(0, mid).join(' ') + '<br/>' + words.slice(mid).join(' ');
    }

    html += '<div class="timeline-node"><div class="sprint-label">Sprint ' + sp.sprint_num + '</div>';
    html += '<div class="theme-label">' + themeDisplay + '</div>';
    html += '<div class="timeline-dot ' + dc + '"></div>';
    html += '<div class="timeline-card">';

    ['EWIP','SC','SCT','RC','ECT'].forEach(kpi => {
      const t = sp.targets[kpi];
      const zc = (t.zone_current || zoneFor(kpi, t.current)).toLowerCase();
      const zt = (t.zone_target || zoneFor(kpi, t.target)).toLowerCase();
      html += '<div class="metric-row"><span class="m-label">' + kpi + '</span>';
      html += '<span><span class="m-' + zc + '">' + fmtVal(kpi, t.current) + '</span>';
      html += ' <span class="m-arrow">\\u2192</span> ';
      html += '<span class="m-' + zt + '">' + fmtVal(kpi, t.target) + '</span></span></div>';
    });

    html += '<div class="timeline-actions">';
    sp.actions.slice(0, 3).forEach(action => {
      const short = action.length <= 50 ? action : action.substring(0, 47) + '...';
      html += '<div class="action-item">' + short + '</div>';
    });
    html += '</div></div></div>';
  });

  html += '</div></div><div class="scroll-hint">\\u2190 scroll horizontally to see all sprints \\u2192</div></section>';

  // Appendix
  html += '<section><h2>Appendix: Per-Sprint Details</h2>';
  data.sprints.forEach((sd, i) => {
    const sname = sprints[i];
    const skpis = sd.kpis;
    const totalTasks = sd.total_tasks || skpis.SC.total_tasks || '?';
    const completed = skpis.SC.completed_in_sprint || '?';

    html += '<div class="sprint-detail"><h3>' + sname + '</h3>';
    html += '<div class="stats">' + totalTasks + ' tasks | ' + completed + ' completed in sprint</div>';
    html += '<div class="kpi-pills">';
    kpis.forEach(kpi => {
      const v = skpis[kpi].value;
      const z = skpis[kpi].zone.toLowerCase();
      html += '<span class="kpi-pill pill-' + z + '">' + kpi + ' ' + fmtVal(kpi, v) + '</span>';
    });
    html += '</div></div>';
  });

  html += '</section></div>';
  html += '<div class="footer">' + teamName + ' Team Sprint Performance Review | Generated ' + dateGen + ' | Sprints ' + shortLabels[0] + '-' + shortLabels[shortLabels.length-1] + '</div>';

  document.getElementById('report-content').innerHTML = html;
  document.getElementById('selector-view').style.display = 'none';
  document.getElementById('report-view').style.display = 'block';
  window.scrollTo(0, 0);
}

function showSelector() {
  document.getElementById('report-view').style.display = 'none';
  document.getElementById('selector-view').style.display = 'flex';
  window.scrollTo(0, 0);
}

(function() {
  if (window._teamGridBuilt) return;
  window._teamGridBuilt = true;
  const grid = document.getElementById('team-grid');
  grid.innerHTML = '';
  const teamNames = Object.keys(TEAMS).sort();
  teamNames.forEach(name => {
    const d = TEAMS[name];
    const h = d.health_rating;
    const filled = Math.round(h);
    const btn = document.createElement('div');
    btn.className = 'team-btn';
    btn.onclick = function() { showTeam(name); };
    btn.innerHTML = '<div>' + name + '</div>' +
      '<div class="health-badge">' + Math.round(h) + '/5 ' +
      '<span class="health-stars">' + '\\u2605'.repeat(filled) + '</span>' +
      '<span class="health-stars-empty">' + '\\u2605'.repeat(5 - filled) + '</span></div>';
    grid.appendChild(btn);
  });
})();
"""


def generate_interactive_html(all_team_data):
    teams_json = json.dumps(all_team_data, ensure_ascii=False)
    js = JAVASCRIPT.replace("__TEAMS_JSON__", teams_json)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sprint Performance Review - Team Selector</title>
<style>{CSS}</style>
</head>
<body>

<!-- TEAM SELECTOR -->
<div id="selector-view" class="selector-screen">
  <!-- Optional: Add your company logo here -->
  <!-- <img src="YOUR_LOGO_URL" alt="Company" class="logo"> -->
  <h1>Sprint Performance Review</h1>
  <div class="subtitle">Select a team to view their improvement plan</div>
  <div id="team-grid" class="team-grid"></div>
</div>

<!-- REPORT (hidden until team is selected) -->
<div id="report-view">
  <button class="back-btn" onclick="showSelector()">&#8592; Back to Teams</button>
  <div id="report-content"></div>
</div>

<script>
{js}
</script>

</body>
</html>"""
    return html


def main():
    args = parse_args()
    all_data = {}

    if args.json_files:
        for f in args.json_files:
            with open(f) as fh:
                d = json.load(fh)
                all_data[d["team"]] = d
        print(f"Loaded {len(all_data)} teams from JSON files")
    else:
        calc_script = find_script("calculate_kpis.py", args.calc_script)
        build_script = find_script("build_improvement_plan.py", args.build_script)
        teams = discover_teams(calc_script, args.data_dir)
        print(f"Found {len(teams)} teams: {teams}")
        for team in teams:
            print(f"  Building plan for {team}...")
            d = build_team_data(build_script, args.data_dir, team)
            if d:
                all_data[team] = d

    if not all_data:
        print("ERROR: No team data available", file=sys.stderr)
        sys.exit(1)

    html = generate_interactive_html(all_data)
    with open(args.output, "w") as f:
        f.write(html)
    print(f"\nInteractive HTML written to {args.output}")
    print(f"  Teams included: {sorted(all_data.keys())}")


if __name__ == "__main__":
    main()
