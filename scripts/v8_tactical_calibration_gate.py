#!/usr/bin/env python3
import csv, json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'tactical_validation' / 'TACTICAL_THRESHOLD_LAB.json'
SUMMARY = ROOT / 'tactical_validation' / 'TACTICAL_VALIDATION_SUMMARY.csv'
QA = ROOT / 'tactical_validation' / 'TACTICAL_VALIDATION_QA.csv'
OUT_JSON = ROOT / 'audit' / 'V8_TACTICAL_CALIBRATION_GATE.json'
OUT_MD = ROOT / 'audit' / 'V8_TACTICAL_CALIBRATION_GATE.md'


def load_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

lab = json.loads(LAB.read_text(encoding='utf-8'))
summary = load_csv(SUMMARY)
qa = load_csv(QA)
c = lab['candidate_for_next_validation']

qa_ok = bool(qa) and all(str(r.get('PASS','')).lower() == 'true' for r in qa)
prod = [r for r in summary if r.get('scope') == 'PRODUCTION']
prod_obs_ok = len(prod) >= 4 and all(int(float(r['observations'])) >= 150 for r in prod)

# Deployment requires positive behavior in both chronological samples, not only a good holdout.
train_positive = (
    float(c['train_mean12']) > 0 and
    float(c['train_median12']) > 0 and
    float(c['train_win12']) >= 50 and
    float(c['train_mean24']) > 0 and
    float(c['train_worst_asset_mean12']) >= 0
)
holdout_positive = (
    float(c['holdout_mean12']) > 0 and
    float(c['holdout_median12']) > 0 and
    float(c['holdout_win12']) >= 50 and
    float(c['holdout_mean24']) > 0 and
    float(c['holdout_worst_asset_mean12']) >= 0
)

production_consistency = all(
    float(r['setup_mean_12h_pct']) > 0 and
    float(r['setup_mean_24h_pct']) > 0
    for r in prod
)

regime_instability = holdout_positive and not train_positive
production_mixed = not production_consistency

deploy_gate = qa_ok and prod_obs_ok and train_positive and holdout_positive and production_consistency
status = 'PASS_DO_BADAN_DALSZYCH__DEPLOY_HOLD' if not deploy_gate else 'DEPLOY_CANDIDATE_REQUIRES_MANUAL_APPROVAL'

reasons = []
if not qa_ok: reasons.append('QA danych walidacyjnych nie jest kompletne')
if not prod_obs_ok: reasons.append('Za mało obserwacji produkcyjnych')
if not train_positive: reasons.append('Próbka TRAIN nie spełnia minimalnego dodatniego profilu')
if regime_instability: reasons.append('Wynik HOLDOUT jest dodatni przy ujemnym TRAIN — ryzyko niestabilności reżimu / selekcji próbki')
if production_mixed: reasons.append('Spójność między aktywami produkcyjnymi jest niewystarczająca')
if not reasons: reasons.append('Bramka ilościowa spełniona, ale wdrożenie nadal wymaga ręcznej decyzji i osobnej walidacji kosztów')

report = {
    'generated_at_utc': datetime.now(timezone.utc).isoformat(),
    'engine': 'V8_TACTICAL_CALIBRATION_GATE_v1.0',
    'research_only': True,
    'production_thresholds_changed': False,
    'auto_execution_changed': False,
    'deployment_gate': deploy_gate,
    'status': status,
    'qa_ok': qa_ok,
    'production_observations_ok': prod_obs_ok,
    'train_positive_gate': train_positive,
    'holdout_positive_gate': holdout_positive,
    'production_cross_asset_consistency_gate': production_consistency,
    'regime_instability_flag': regime_instability,
    'candidate': c,
    'production_assets': [r['symbol'] for r in prod],
    'reasons': reasons,
    'decision': 'NIE ZMIENIAĆ PRODUKCYJNYCH PROGÓW' if not deploy_gate else 'KANDYDAT DO KOLEJNEJ WALIDACJI — BEZ AUTOMATYCZNEGO WDROŻENIA'
}
OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

lines = [
    '# V8 TACTICAL — BRAMKA KALIBRACJI', '',
    f"Status: **{status}**", '',
    '## Wynik',
    f"- QA danych: {'PASS' if qa_ok else 'FAIL'}",
    f"- Minimalna liczba obserwacji: {'PASS' if prod_obs_ok else 'FAIL'}",
    f"- TRAIN: {'PASS' if train_positive else 'FAIL'}",
    f"- HOLDOUT: {'PASS' if holdout_positive else 'FAIL'}",
    f"- Spójność między aktywami produkcyjnymi: {'PASS' if production_consistency else 'FAIL'}",
    f"- Flaga niestabilności reżimu: {'TAK' if regime_instability else 'NIE'}", '',
    '## Kandydat badawczy',
    f"- score_min = {c['score_min']}",
    f"- fomo_max = {c['fomo_max']}",
    f"- trend4_min = {c['trend4_min']}",
    f"- RSI = {c['rsi_lo']}–{c['rsi_hi']}",
    f"- TRAIN mean 12h = {c['train_mean12']:.4f}% | win = {c['train_win12']:.2f}%",
    f"- HOLDOUT mean 12h = {c['holdout_mean12']:.4f}% | win = {c['holdout_win12']:.2f}%", '',
    '## Decyzja',
    f"**{report['decision']}**", '',
    'Powody:'
]
lines += [f'- {x}' for x in reasons]
lines += ['', 'Ta bramka nie modyfikuje SILNIK_TACTICAL, panelu, progów produkcyjnych ani AUTO EXECUTION.']
OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
