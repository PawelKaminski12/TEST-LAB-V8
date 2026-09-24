from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'google_sheets' / 'DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt'
RADAR = ROOT / 'scripts' / 'v8_morning_radar.py'
TACTICAL_WF = ROOT / '.github' / 'workflows' / 'test-lab-v8-tactical-engine.yml'
RADAR_WF = ROOT / '.github' / 'workflows' / 'test-lab-v8-morning-radar.yml'


def must_replace(text, old, new, name):
    if old not in text:
        raise SystemExit(f'missing pattern: {name}')
    return text.replace(old, new, 1)

# ---------- Apps Script ----------
s = APP.read_text(encoding='utf-8')

# Do not rebuild morning layout inside generic setup. Morning sheet is recreated only when rendered.
s = must_replace(
    s,
    "  setupMorningBrief_(ss.getSheetByName(V10_MORNING_SHEET));\n",
    "  // PORANNY_BRIEF jest odbudowywany atomowo dopiero przy renderowaniu.\n",
    'V8_SETUP morning setup',
)

# Fresh morning sheet helper: delete old sheet as a whole; never touch its legacy merge state.
anchor = "function setupMorningBrief_(sheet) {\n"
helper = r'''function freshMorningSheetV10_(ss) {
  const old = ss.getSheetByName(V10_MORNING_SHEET);
  let index = null;
  if (old) {
    index = old.getIndex();
    ss.deleteSheet(old);
  }
  return index ? ss.insertSheet(V10_MORNING_SHEET, index) : ss.insertSheet(V10_MORNING_SHEET);
}

function setupMorningBrief_(sheet) {
'''
s = must_replace(s, anchor, helper, 'freshMorningSheet helper')

# setup is called only on a freshly created sheet; no unmerge calls.
s = must_replace(
    s,
    "function setupMorningBrief_(sheet) {\n  unmergeAllSafelyV10_(sheet);\n",
    "function setupMorningBrief_(sheet) {\n",
    'remove morning unmerge',
)

# Full refresh: render onto a freshly recreated morning sheet.
s = must_replace(
    s,
    "    writeMorningRadarBrief_(ss.getSheetByName(V10_MORNING_SHEET), morningRadarJson);\n",
    "    const morningSheetV10 = freshMorningSheetV10_(ss);\n    writeMorningRadarBrief_(morningSheetV10, morningRadarJson);\n",
    'ODSWIEZ_WSZYSTKO fresh morning',
)

# Morning-only refresh: same atomic rebuild.
s = must_replace(
    s,
    "  const sheet = getOrCreateSheet_(ss, V10_MORNING_SHEET);\n  const radarJson = JSON.parse(fetchText_(V10_MORNING_RADAR_URL));\n",
    "  const sheet = freshMorningSheetV10_(ss);\n  const radarJson = JSON.parse(fetchText_(V10_MORNING_RADAR_URL));\n",
    'ODSWIEZ_PORANNY_BRIEF fresh morning',
)

# Manual mode switch: recreate and render from cached JSON instead of touching old merged sheet.
s = must_replace(
    s,
    "      writeMorningRadarBrief_(sheet, JSON.parse(cached));\n      SpreadsheetApp.getActiveSpreadsheet().toast('Radar przełączony na ' + mode, 'V8', 2);\n",
    "      const ss = SpreadsheetApp.getActiveSpreadsheet();\n      const freshSheet = freshMorningSheetV10_(ss);\n      writeMorningRadarBrief_(freshSheet, JSON.parse(cached));\n      ss.toast('Radar przełączony na ' + mode, 'V8', 2);\n",
    'selection fresh morning',
)

# Freshness + timestamp helpers.
anchor = "function macdBriefV10_(v) {\n"
helpers = r'''function morningFreshnessV10_(x) {
  const tf = String((x && x.timeframe) || '').toUpperCase();
  const limits = {'1H':3, '2H':5, '4H':10};
  const limit = limits[tf] || 3;
  const raw = String((x && x.last_close_time_utc) || '');
  if (!raw) return {fresh:false, ageHours:'', limitHours:limit};
  const t = new Date(raw);
  if (isNaN(t.getTime())) return {fresh:false, ageHours:'', limitHours:limit};
  const age = Math.max(0, (Date.now() - t.getTime()) / 3600000);
  const sourceStale = Boolean(x && x.stale);
  return {fresh: !sourceStale && age <= limit, ageHours: Math.round(age * 10) / 10, limitHours: limit};
}

function morningTimePlV10_(iso) {
  if (!iso) return '';
  const d = new Date(String(iso));
  if (isNaN(d.getTime())) return '';
  return Utilities.formatDate(d, 'Europe/Warsaw', 'HH:mm');
}

function morningReasonV10_(x, freshness) {
  const base = String((x && x.reason_pl) || 'brak skrajności');
  const last = morningTimePlV10_(x && x.last_close_time_utc);
  if (!freshness.fresh) {
    return 'STARE DANE' + (last ? ' — ostatnia świeca ' + last : '');
  }
  if (base.toLowerCase() === 'brak skrajności') return base;
  const started = morningTimePlV10_(x && x.signal_started_at_utc);
  return base + (started ? ' (' + started + ')' : '');
}

function macdBriefV10_(v) {
'''
s = must_replace(s, anchor, helpers, 'morning freshness helpers')

old_map = r'''  const assets = (radarJson.assets || []).map(a => {
    const x = morningRadarTfV10_(a, mode);
    return {
      sym: String(a.symbol || ''),
      tf: String(x.timeframe || (mode === 'AUTO' ? (a.auto || {}).timeframe : mode) || ''),
      rsi: round1V10_(x.rsi14),
      mfi: round1V10_(x.mfi14),
      macd: String(x.macd_display_pl || macdBriefV10_(x.macd_extreme_label)),
      fomo: Number(x.fomo_score_0_10 || 0),
      trend: Number(x.trend_score_0_4 || 0),
      radar: String(x.radar_status || 'BRAK'),
      intensity: Number(x.radar_intensity_0_10 || 0),
      dir: String(x.radar_direction || 'NEUTRAL'),
      reason: String(x.reason_pl || 'brak skrajności'),
      rsiExtreme: Boolean(x.rsi_extreme),
      mfiExtreme: Boolean(x.mfi_extreme),
      macdAlert: Boolean(x.macd_alert),
      fomoHard: Boolean(x.fomo_hard),
      stale: Boolean(x.stale)
    };
  }).filter(x => x.sym);
'''
new_map = r'''  const assets = (radarJson.assets || []).map(a => {
    const x = morningRadarTfV10_(a, mode);
    const freshness = morningFreshnessV10_(x);
    return {
      sym: String(a.symbol || ''),
      tf: String(x.timeframe || (mode === 'AUTO' ? (a.auto || {}).timeframe : mode) || ''),
      rsi: round1V10_(x.rsi14),
      mfi: round1V10_(x.mfi14),
      macd: freshness.fresh ? String(x.macd_display_pl || macdBriefV10_(x.macd_extreme_label)) : 'STARE',
      fomo: Number(x.fomo_score_0_10 || 0),
      trend: Number(x.trend_score_0_4 || 0),
      radar: freshness.fresh ? String(x.radar_status || 'BRAK') : 'STARE DANE',
      intensity: freshness.fresh ? Number(x.radar_intensity_0_10 || 0) : 0,
      dir: freshness.fresh ? String(x.radar_direction || 'NEUTRAL') : 'NEUTRAL',
      reason: morningReasonV10_(x, freshness),
      rsiExtreme: freshness.fresh && Boolean(x.rsi_extreme),
      mfiExtreme: freshness.fresh && Boolean(x.mfi_extreme),
      macdAlert: freshness.fresh && Boolean(x.macd_alert),
      fomoHard: freshness.fresh && Boolean(x.fomo_hard),
      stale: !freshness.fresh,
      ageHours: freshness.ageHours,
      limitHours: freshness.limitHours
    };
  }).filter(x => x.sym);
'''
s = must_replace(s, old_map, new_map, 'morning asset mapping')

s = must_replace(
    s,
    "  const neutral = assets.filter(x => x.dir === 'NEUTRAL').length;\n",
    "  const neutral = assets.filter(x => !x.stale && x.dir === 'NEUTRAL').length;\n",
    'neutral excludes stale',
)
s = must_replace(
    s,
    "  const priority = assets.slice().sort((a,b)=>(b.intensity-a.intensity)||(b.fomo-a.fomo)).slice(0,5);\n",
    "  const priority = assets.filter(x => !x.stale).slice().sort((a,b)=>(b.intensity-a.intensity)||(b.fomo-a.fomo)).slice(0,5);\n",
    'priority excludes stale',
)
s = must_replace(
    s,
    "  const watch = assets.filter(x => x.intensity > 0 && x.intensity < 5)\n",
    "  const watch = assets.filter(x => !x.stale && x.intensity > 0 && x.intensity < 5)\n",
    'watch excludes stale',
)

s = must_replace(
    s,
    "  const status = String(sheet.getRange(r,8).getDisplayValue() || '').toUpperCase();\n  const macd = String(sheet.getRange(r,5).getDisplayValue() || '').toUpperCase();\n",
    "  const status = String(sheet.getRange(r,8).getDisplayValue() || '').toUpperCase();\n  if (status.indexOf('STARE') >= 0) return 'INFO';\n  const macd = String(sheet.getRange(r,5).getDisplayValue() || '').toUpperCase();\n",
    'stale row info color',
)

APP.write_text(s, encoding='utf-8')

# ---------- Morning radar generator ----------
r = RADAR.read_text(encoding='utf-8')
r = must_replace(r, "TF_ORDER = ['1H', '2H', '4H']\n", "TF_ORDER = ['1H', '2H', '4H']\nFRESH_LIMIT_H = {'1H': 3, '2H': 5, '4H': 10}\n", 'freshness constants')

insert_after = "def compact_tf(tf):\n"
extra = r'''def freshness_state(tf_name, tf):
    raw = tf.get('last_close_time_utc')
    if not raw:
        return True, None
    try:
        last = pd.Timestamp(raw)
        if last.tzinfo is None:
            last = last.tz_localize('UTC')
        else:
            last = last.tz_convert('UTC')
        age_h = (pd.Timestamp.now(tz='UTC') - last).total_seconds() / 3600.0
        return bool(age_h > FRESH_LIMIT_H[tf_name]), round(max(0.0, age_h), 2)
    except Exception:
        return True, None


def signal_signature(tf):
    reason = str(tf.get('reason_pl') or 'brak skrajności')
    if reason.lower() == 'brak skrajności':
        return None
    return '|'.join([
        reason,
        str(tf.get('radar_status') or ''),
        str(tf.get('macd_display_pl') or ''),
    ])


def previous_tf(previous, symbol, tf_name):
    for a in (previous or {}).get('assets', []):
        if str(a.get('symbol') or '') == symbol:
            return ((a.get('timeframes') or {}).get(tf_name) or {})
    return {}


def attach_signal_start(symbol, tf_name, tf, previous):
    sig = signal_signature(tf)
    prev = previous_tf(previous, symbol, tf_name)
    prev_sig = prev.get('signal_signature')
    if sig is None:
        tf['signal_signature'] = None
        tf['signal_started_at_utc'] = None
        return tf
    tf['signal_signature'] = sig
    if prev_sig == sig and prev.get('signal_started_at_utc'):
        tf['signal_started_at_utc'] = prev.get('signal_started_at_utc')
    else:
        tf['signal_started_at_utc'] = tf.get('last_close_time_utc') or datetime.now(timezone.utc).isoformat()
    return tf


def compact_tf(tf):
'''
r = must_replace(r, insert_after, extra, 'generator helpers')

# main previous load
r = must_replace(
    r,
    "def main():\n    data = json.loads(TACTICAL_JSON.read_text(encoding='utf-8'))\n",
    "def main():\n    previous = {}\n    if OUT_JSON.exists():\n        try:\n            previous = json.loads(OUT_JSON.read_text(encoding='utf-8'))\n        except Exception:\n            previous = {}\n    data = json.loads(TACTICAL_JSON.read_text(encoding='utf-8'))\n",
    'load previous radar',
)

old_tfs = "            tfs = {'1H': t1, '2H': t2, '4H': t4}\n            ranked = sorted(\n"
new_tfs = "            tfs = {'1H': t1, '2H': t2, '4H': t4}\n            for tf_name, tf_state in tfs.items():\n                stale, age_h = freshness_state(tf_name, tf_state)\n                tf_state['stale'] = stale\n                tf_state['age_hours'] = age_h\n                tf_state['fresh_limit_hours'] = FRESH_LIMIT_H[tf_name]\n                attach_signal_start(sym, tf_name, tf_state, previous)\n            ranked = sorted(\n"
r = must_replace(r, old_tfs, new_tfs, 'normalize freshness and signal start')

RADAR.write_text(r, encoding='utf-8')

# ---------- Workflow schedules ----------
w = TACTICAL_WF.read_text(encoding='utf-8')
w = must_replace(w, "    - cron: '15 */4 * * *'\n", "    - cron: '5 * * * *'\n", 'tactical hourly schedule')
TACTICAL_WF.write_text(w, encoding='utf-8')

w = RADAR_WF.read_text(encoding='utf-8')
w = must_replace(
    w,
    "                  assert x['closed_bar_only'] is True\n                  assert x['stale'] is False\n",
    "                  assert x['closed_bar_only'] is True\n                  assert isinstance(x['stale'], bool)\n                  assert x['fresh_limit_hours'] in (3, 5, 10)\n                  assert 'signal_started_at_utc' in x\n",
    'radar validation freshness',
)
RADAR_WF.write_text(w, encoding='utf-8')

print('PATCH OK: atomic morning rebuild + hourly source + freshness + POWOD time')
