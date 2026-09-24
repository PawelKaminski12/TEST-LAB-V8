from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')
marker = '// ===== V10 SHARED INDICATOR LANGUAGE ====='
if marker in s:
    s = s.split(marker)[0].rstrip() + '\n'

patch = r'''

// ===== V10 SHARED INDICATOR LANGUAGE =====
// Jedna warstwa języka dla wszystkich widoków V8.
// Nie zmienia progów ani obliczeń Tactical/LONG — ujednolica tylko znaczenie i opis sygnałów.
function macdDisplayLabelV10_(x) {
  const src = String((x && x.macd_extreme_label) || 'NORMAL').toUpperCase();
  const hist = Number(x && x.macd_hist);
  if (src === 'NORMAL' || src === 'NO_DATA' || !Number.isFinite(hist)) return 'NORMALNY';
  const extreme = src.indexOf('EXTREME') >= 0;
  const warning = src.indexOf('WARNING') >= 0;
  if (!extreme && !warning) return 'NORMALNY';
  if (hist > 0) return extreme ? 'MACD EKSTREMUM + — GÓRNE GRANICE' : 'MACD UWAGA + — GÓRNA STREFA';
  if (hist < 0) return extreme ? 'MACD EKSTREMUM − — DOLNE GRANICE' : 'MACD UWAGA − — DOLNA STREFA';
  return 'NORMALNY';
}

function extremeLabel_(x, cfg) {
  const rsi = Number(x.rsi14), mfi = Number(x.mfi14), fomo = Number(x.fomo_score_0_10), labels = [];
  if (Number.isFinite(rsi) && rsi >= cfg.rsiHigh) labels.push(rsi >= 80 ? 'RSI GÓRNE GRANICE' : 'RSI GÓRNA STREFA');
  if (Number.isFinite(rsi) && rsi <= cfg.rsiLow) labels.push(rsi <= 20 ? 'RSI DOLNE GRANICE' : 'RSI DOLNA STREFA');
  if (Number.isFinite(mfi)) {
    if (mfi >= cfg.mfiExtremeHigh) labels.push('MFI GÓRNE GRANICE');
    else if (mfi >= cfg.mfiWarnHigh) labels.push('MFI GÓRNA STREFA');
    if (mfi <= cfg.mfiExtremeLow) labels.push('MFI DOLNE GRANICE');
    else if (mfi <= cfg.mfiWarnLow) labels.push('MFI DOLNA STREFA');
  }
  const macd = macdDisplayLabelV10_(x);
  if (macd !== 'NORMALNY') labels.push(macd);
  if (Number.isFinite(fomo) && fomo >= cfg.fomoHard) labels.push(fomo >= 9 ? 'FOMO GÓRNE GRANICE' : 'FOMO GÓRNA STREFA');
  return labels.length ? labels.join(' + ') : 'BRAK';
}

function alarmDirection_(a) {
  const signals = a.signals || [];
  let hot = 0, cold = 0;
  signals.forEach(s => {
    const x = String(s || '').toUpperCase();
    if (x.indexOf('GÓRNE') >= 0 || x.indexOf('GÓRNA') >= 0 || x.indexOf('FOMO') >= 0) hot++;
    if (x.indexOf('DOLNE') >= 0 || x.indexOf('DOLNA') >= 0) cold++;
    // zgodność wsteczna ze starszym nazewnictwem podczas jednego cyklu migracji
    if (x.indexOf('WYKUPIENIE') >= 0 || x.indexOf('DODATNIE') >= 0) hot++;
    if (x.indexOf('WYPRZEDANIE') >= 0 || x.indexOf('UJEMNE') >= 0) cold++;
  });
  if (hot > 0 && cold === 0) return 'PRZEGRZANIE';
  if (cold > 0 && hot === 0) return 'WYPRZEDANIE';
  return 'MIESZANE';
}

function buildExtremeAlarms_(ss, tacticalJson) {
  const cfg = getExtremeSettings_(ss);
  if (!cfg.enabled) return [];
  const base = [];
  (tacticalJson.assets || []).forEach(a => {
    const t = a.timeframes || {};
    ['1H','4H','1D'].forEach(tf => {
      const x = t[tf] || {};
      const rsi = Number(x.rsi14), mfi = Number(x.mfi14), fomo = Number(x.fomo_score_0_10);
      const macdPct = Number(x.macd_hist_percentile), macdZ = Number(x.macd_hist_zscore);
      const ts = x.last_close_time_utc || '';
      const signals = [];

      if (Number.isFinite(rsi) && rsi >= cfg.rsiHigh) signals.push(rsi >= 80 ? 'RSI GÓRNE GRANICE' : 'RSI GÓRNA STREFA');
      if (Number.isFinite(rsi) && rsi <= cfg.rsiLow) signals.push(rsi <= 20 ? 'RSI DOLNE GRANICE' : 'RSI DOLNA STREFA');

      if (Number.isFinite(mfi)) {
        if (mfi >= cfg.mfiExtremeHigh) signals.push('MFI GÓRNE GRANICE');
        else if (mfi >= cfg.mfiWarnHigh) signals.push('MFI GÓRNA STREFA');
        if (mfi <= cfg.mfiExtremeLow) signals.push('MFI DOLNE GRANICE');
        else if (mfi <= cfg.mfiWarnLow) signals.push('MFI DOLNA STREFA');
      }

      const macd = macdDisplayLabelV10_(x);
      if (macd !== 'NORMALNY') signals.push(macd);

      if (Number.isFinite(fomo) && fomo >= cfg.fomoHard) signals.push(fomo >= 9 ? 'FOMO GÓRNE GRANICE' : 'FOMO GÓRNA STREFA');
      if (!signals.length) return;

      const count = signals.length;
      const priority = confluencePriorityForTf_(count, tf);
      const tfWeight = timeframeWeight_(tf);
      const freshness = alarmFreshness_(tf, ts, cfg);
      const n = count === 1 ? '1 sygnał' : count < 5 ? count+' sygnały' : count+' sygnałów';
      const reason = a.symbol+' '+tf+': '+n+' zgodne. Priorytet '+priority+', waga '+tfWeight+', świeżość '+freshness.status+(freshness.ageHours === '' ? '' : ' ('+freshness.ageHours+'h / limit '+freshness.limitHours+'h)')+'. '+signals.join(' + ')+'.';
      base.push({
        aktywny:freshness.fresh,symbol:a.symbol,tf:tf,type:signals.join(' + '),signalCount:count,
        priority:priority,severity:priority,tfWeight:tfWeight,signals:signals,
        rsi:Number.isFinite(rsi)?rsi:'',mfi:Number.isFinite(mfi)?mfi:'',macdPct:Number.isFinite(macdPct)?macdPct:'',
        macdZ:Number.isFinite(macdZ)?macdZ:'',fomo:Number.isFinite(fomo)?fomo:'',reason:reason,ts:ts,
        freshness:freshness.status,ageHours:freshness.ageHours,limitHours:freshness.limitHours,
        key:[a.symbol,tf,signals.join(' + ')].join('|')
      });
    });
  });
  return base.concat(buildMultiTfConfluence_(base)).sort(compareExtremeFreshnessPriorityV7_);
}
'''

p.write_text(s.rstrip() + patch + '\n', encoding='utf-8')
print('Applied shared V10 indicator language: RSI/MFI/MACD/FOMO upper/lower semantics')
