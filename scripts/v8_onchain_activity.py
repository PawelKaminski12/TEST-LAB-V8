import json
import math
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests

OUT = Path("crypto_data_hub")
OUT.mkdir(exist_ok=True)
CFG = Path("config/alt_universe.csv")

ASSET_MAP = {
    "ETH": {"cm": "eth", "chain": "Ethereum", "protocol": None, "profile": "CHAIN_L1"},
    "SOL": {"cm": "sol", "chain": "Solana", "protocol": None, "profile": "CHAIN_L1"},
    "LINK": {"cm": "link", "chain": None, "protocol": None, "profile": "ORACLE_INFRA"},
    "ONDO": {"cm": "ondo", "chain": None, "protocol": "ondo-finance", "profile": "RWA_PROTOCOL"},
}
METRICS = ["AdrActCnt", "TxCnt", "TxTfrValAdjUSD"]
CM = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
LLAMA = "https://api.llama.fi"
STABLE = "https://stablecoins.llama.fi"

session = requests.Session()
session.headers.update({"User-Agent": "TEST-LAB-V8/1.6"})
end = datetime.now(timezone.utc)
start = end - timedelta(days=90)


def safe_float(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def pct(a, b):
    a = safe_float(a)
    b = safe_float(b)
    if a is None or b in (None, 0):
        return None
    return (a / b - 1.0) * 100.0


def trend_label(v7, v30):
    vals = [v for v in (v7, v30) if v is not None]
    if not vals:
        return "NO_DATA"
    avg = sum(vals) / len(vals)
    if avg >= 10:
        return "STRONG_RISING"
    if avg >= 2:
        return "RISING"
    if avg <= -10:
        return "STRONG_FALLING"
    if avg <= -2:
        return "FALLING"
    return "FLAT"


def point_change(series, days):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 2:
        return None
    idx = max(0, len(s) - 1 - days)
    return pct(float(s.iloc[-1]), float(s.iloc[idx]))


def sum_change(series, days):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < days * 2:
        return None
    return pct(float(s.iloc[-days:].sum()), float(s.iloc[-2 * days : -days].sum()))


def get_json(url, params=None, timeout=25, retries=3):
    last = "NO_DATA"
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                try:
                    return r.json(), "OK"
                except Exception:
                    last = "BAD_JSON"
            else:
                last = f"HTTP_{r.status_code}"
        except Exception as e:
            last = "ERROR_" + type(e).__name__
        time.sleep(attempt * 1.2)
    return None, last


def cm_series(asset):
    obj, status = get_json(
        CM,
        {
            "assets": asset,
            "metrics": ",".join(METRICS),
            "frequency": "1d",
            "start_time": start.isoformat().replace("+00:00", "Z"),
            "end_time": end.isoformat().replace("+00:00", "Z"),
            "page_size": 10000,
        },
        20,
        2,
    )
    if status != "OK" or not isinstance(obj, dict):
        return pd.DataFrame(), status
    data = obj.get("data", [])
    if not data:
        return pd.DataFrame(), "NO_DATA"
    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    for m in METRICS:
        if m in df.columns:
            df[m] = pd.to_numeric(df[m], errors="coerce")
    return df.sort_values("time"), "OK"


def generic_series(url, value_key, params=None, list_mode=True):
    obj, status = get_json(url, params=params, timeout=20)
    if status != "OK":
        return pd.DataFrame(), status
    rows = []
    if list_mode and isinstance(obj, list):
        for x in obj:
            if not isinstance(x, dict):
                continue
            ts = x.get("date")
            val = safe_float(x.get(value_key))
            if ts is not None and val is not None:
                rows.append({"date": ts, "value": val})
    if not rows:
        return pd.DataFrame(), "NO_DATA"
    df = pd.DataFrame(rows)
    df["date_num"] = pd.to_numeric(df["date"], errors="coerce")
    df["date"] = pd.to_datetime(df["date_num"], unit="s", utc=True, errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["date", "value"]).sort_values("date").tail(120)[["date", "value"]], "OK"


def chain_tvl(chain):
    if not chain:
        return pd.DataFrame(), "NOT_APPLICABLE"
    return generic_series(f"{LLAMA}/v2/historicalChainTvl/{chain}", "tvl")


def chart_series(url, params=None):
    obj, status = get_json(url, params=params, timeout=20)
    if status != "OK" or not isinstance(obj, dict):
        return pd.DataFrame(), status
    chart = obj.get("totalDataChart") or []
    rows = [{"date": x[0], "value": x[1]} for x in chart if isinstance(x, list) and len(x) >= 2]
    if not rows:
        return pd.DataFrame(), "NO_DATA"
    df = pd.DataFrame(rows)
    df["date_num"] = pd.to_numeric(df["date"], errors="coerce")
    df["date"] = pd.to_datetime(df["date_num"], unit="s", utc=True, errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["date", "value"]).sort_values("date").tail(120)[["date", "value"]], "OK"


def dex_series(chain):
    if not chain:
        return pd.DataFrame(), "NOT_APPLICABLE"
    return chart_series(
        f"{LLAMA}/overview/dexs/{chain}",
        {
            "excludeTotalDataChart": "false",
            "excludeTotalDataChartBreakdown": "true",
            "dataType": "dailyVolume",
        },
    )


def fees_series(chain):
    if not chain:
        return pd.DataFrame(), "NOT_APPLICABLE"
    return chart_series(
        f"{LLAMA}/overview/fees/{chain}",
        {
            "excludeTotalDataChart": "false",
            "excludeTotalDataChartBreakdown": "true",
            "dataType": "dailyFees",
        },
    )


def stablecoin_series(chain):
    if not chain:
        return pd.DataFrame(), "NOT_APPLICABLE"
    obj, status = get_json(f"{STABLE}/stablecoincharts/{chain}", timeout=20)
    if status != "OK" or not isinstance(obj, list):
        return pd.DataFrame(), status
    rows = []
    for x in obj:
        if not isinstance(x, dict):
            continue
        ts = x.get("date")
        total = x.get("totalCirculatingUSD")
        if isinstance(total, dict):
            val = safe_float(total.get("peggedUSD"))
            if val is None:
                vals = [safe_float(v) for v in total.values()]
                vals = [v for v in vals if v is not None]
                val = sum(vals) if vals else None
        else:
            val = safe_float(total)
        if ts is not None and val is not None:
            rows.append({"date": ts, "value": val})
    if not rows:
        return pd.DataFrame(), "NO_DATA"
    df = pd.DataFrame(rows)
    df["date_num"] = pd.to_numeric(df["date"], errors="coerce")
    df["date"] = pd.to_datetime(df["date_num"], unit="s", utc=True, errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"]).sort_values("date").tail(120)[["date", "value"]]
    if df.empty:
        return pd.DataFrame(), "NO_DATA_AFTER_PARSE"
    return df, "OK"


def _latest_from_chain_tvls(obj):
    chain_tvls = obj.get("chainTvls") or {}
    latest = []
    if not isinstance(chain_tvls, dict):
        return None
    for _, block in chain_tvls.items():
        if not isinstance(block, dict):
            continue
        hist = block.get("tvl") or []
        if isinstance(hist, list) and hist:
            vals = []
            for x in hist:
                if isinstance(x, dict):
                    v = safe_float(x.get("totalLiquidityUSD"))
                    ts = safe_float(x.get("date")) or 0
                    if v is not None:
                        vals.append((ts, v))
            if vals:
                latest.append(max(vals, key=lambda z: z[0])[1])
    return sum(latest) if latest else None


def protocol_snapshot(slug):
    if not slug:
        return {}, "NOT_APPLICABLE"
    result = {}
    obj, status = get_json(f"{LLAMA}/protocol/{slug}", timeout=25)
    if status == "OK" and isinstance(obj, dict):
        result["name"] = obj.get("name")
        result["slug"] = obj.get("slug") or slug
        result["chain_tvls_sum"] = _latest_from_chain_tvls(obj)
        hist = obj.get("tvl") if isinstance(obj.get("tvl"), list) else []
        rows = []
        for x in hist:
            if isinstance(x, dict) and x.get("date") is not None:
                val = safe_float(x.get("totalLiquidityUSD"))
                if val is not None:
                    rows.append({"date": x["date"], "value": val})
        if rows:
            df = pd.DataFrame(rows)
            df["date_num"] = pd.to_numeric(df["date"], errors="coerce")
            df["date"] = pd.to_datetime(df["date_num"], unit="s", utc=True, errors="coerce")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            result["history"] = df.dropna(subset=["date", "value"]).sort_values("date").tail(120)[["date", "value"]]

    plist, pstatus = get_json(f"{LLAMA}/protocols", timeout=30)
    if pstatus == "OK" and isinstance(plist, list):
        exact = []
        fallback = []
        for x in plist:
            if not isinstance(x, dict):
                continue
            name = str(x.get("name") or "").strip().lower()
            s = str(x.get("slug") or "").strip().lower()
            category = str(x.get("category") or "").strip().lower()
            if s == slug.lower() or name == "ondo finance":
                exact.append(x)
            elif slug == "ondo-finance" and "ondo" in name and ("rwa" in category or "derivative" in category):
                fallback.append(x)
        candidates = exact or fallback
        if candidates:
            best = max(candidates, key=lambda z: safe_float(z.get("tvl")) or -1)
            tvl = safe_float(best.get("tvl"))
            if tvl is not None and (slug != "ondo-finance" or tvl >= 10_000_000):
                result["protocols_tvl"] = tvl
                result["change_7d"] = safe_float(best.get("change_7d"))
                result["change_1m"] = safe_float(best.get("change_1m"))
                result["protocols_name"] = best.get("name")
                result["protocols_slug"] = best.get("slug")

    if not result:
        return {}, status if status != "OK" else pstatus
    return result, "OK"


def protocol_fees(slug):
    if not slug:
        return {}, "NOT_APPLICABLE"
    obj, status = get_json(
        f"{LLAMA}/summary/fees/{slug}",
        {
            "dataType": "dailyFees",
            "excludeTotalDataChart": "false",
            "excludeTotalDataChartBreakdown": "true",
        },
        20,
    )
    if status != "OK" or not isinstance(obj, dict):
        return {}, status
    out = {
        "total24h": safe_float(obj.get("total24h")),
        "total7d": safe_float(obj.get("total7d")),
        "total30d": safe_float(obj.get("total30d")),
    }
    chart = obj.get("totalDataChart") or []
    rows = [{"date": x[0], "value": x[1]} for x in chart if isinstance(x, list) and len(x) >= 2]
    if rows:
        df = pd.DataFrame(rows)
        df["date_num"] = pd.to_numeric(df["date"], errors="coerce")
        df["date"] = pd.to_datetime(df["date_num"], unit="s", utc=True, errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        out["history"] = df.dropna(subset=["date", "value"]).sort_values("date").tail(120)[["date", "value"]]
    return out, "OK"


def point_block(df):
    out = {"latest_usd": None, "change_7d_pct": None, "change_30d_pct": None, "trend": "NO_DATA"}
    if df.empty or "value" not in df.columns:
        return out
    s = df["value"].dropna()
    if s.empty:
        return out
    c7 = point_change(s, 7)
    c30 = point_change(s, 30)
    return {"latest_usd": safe_float(s.iloc[-1]), "change_7d_pct": c7, "change_30d_pct": c30, "trend": trend_label(c7, c30)}


def flow_block(df):
    out = {"latest_daily_usd": None, "change_7d_vs_prev7_pct": None, "change_30d_vs_prev30_pct": None, "trend": "NO_DATA"}
    if df.empty or "value" not in df.columns:
        return out
    s = df["value"].dropna()
    if s.empty:
        return out
    c7 = sum_change(s, 7)
    c30 = sum_change(s, 30)
    return {"latest_daily_usd": safe_float(s.iloc[-1]), "change_7d_vs_prev7_pct": c7, "change_30d_vs_prev30_pct": c30, "trend": trend_label(c7, c30)}


def protocol_tvl_block(snapshot):
    out = {"latest_usd": None, "change_7d_pct": None, "change_30d_pct": None, "trend": "NO_DATA", "quality": "NO_DATA"}
    if not snapshot:
        return out
    hist = snapshot.get("history")
    if isinstance(hist, pd.DataFrame) and not hist.empty:
        b = point_block(hist)
        ref = safe_float(snapshot.get("protocols_tvl") or snapshot.get("chain_tvls_sum"))
        if ref is not None and b["latest_usd"] is not None and ref > 0:
            ratio = b["latest_usd"] / ref
            if 0.5 <= ratio <= 1.5:
                b["quality"] = "HISTORY_CONFIRMED"
                return b
    latest = safe_float(snapshot.get("protocols_tvl") or snapshot.get("chain_tvls_sum"))
    if latest is None:
        return out
    c7 = safe_float(snapshot.get("change_7d"))
    c30 = safe_float(snapshot.get("change_1m"))
    return {"latest_usd": latest, "change_7d_pct": c7, "change_30d_pct": c30, "trend": trend_label(c7, c30), "quality": "SNAPSHOT_EXACT"}


def protocol_fees_block(data):
    out = {"fees_24h_usd": None, "fees_7d_usd": None, "fees_30d_usd": None, "change_7d_vs_prev7_pct": None, "change_30d_vs_prev30_pct": None, "trend": "NO_DATA"}
    if not data:
        return out
    out["fees_24h_usd"] = safe_float(data.get("total24h"))
    out["fees_7d_usd"] = safe_float(data.get("total7d"))
    out["fees_30d_usd"] = safe_float(data.get("total30d"))
    hist = data.get("history")
    if isinstance(hist, pd.DataFrame) and not hist.empty:
        s = hist["value"].dropna()
        c7 = sum_change(s, 7)
        c30 = sum_change(s, 30)
        out["change_7d_vs_prev7_pct"] = c7
        out["change_30d_vs_prev30_pct"] = c30
        out["trend"] = trend_label(c7, c30)
    return out


def context(votes):
    votes = [v for v in votes if v is not None]
    if not votes:
        return {"score": None, "label": "NO_DATA", "votes": 0}
    pos = sum(v > 2 for v in votes)
    neg = sum(v < -2 for v in votes)
    n = len(votes)
    score = max(0, min(10, round((pos - neg + n) / (2 * n) * 10)))
    label = "STRONG_POSITIVE" if score >= 8 else "POSITIVE" if score >= 6 else "NEUTRAL" if score >= 4 else "NEGATIVE" if score >= 2 else "STRONG_NEGATIVE"
    return {"score": score, "label": label, "votes": n}


def main():
    cfg = pd.read_csv(CFG)
    cfg = cfg[cfg["enabled"].astype(str).str.lower().eq("true")].copy()
    symbols = [str(x).upper().strip() for x in cfg["symbol"].tolist() if str(x).upper().strip() in ASSET_MAP]
    assets = []
    raw_rows = []

    for sym in symbols:
        meta = ASSET_MAP[sym]
        cm, cm_status = cm_series(meta["cm"])
        ctv, ctv_status = chain_tvl(meta["chain"])
        dex, dex_status = dex_series(meta["chain"])
        stable, stable_status = stablecoin_series(meta["chain"])
        fees, fees_status = fees_series(meta["chain"])
        psnap, psnap_status = protocol_snapshot(meta["protocol"])
        pfees, pfees_status = protocol_fees(meta["protocol"])

        metrics = {}
        for m in METRICS:
            if m in cm.columns and cm[m].notna().any():
                ss = cm[m].dropna()
                c7 = point_change(ss, 7)
                c30 = point_change(ss, 30)
                metrics[m] = {"latest": safe_float(ss.iloc[-1]), "change_7d_pct": c7, "change_30d_pct": c30, "trend": trend_label(c7, c30)}
            else:
                metrics[m] = {"latest": None, "change_7d_pct": None, "change_30d_pct": None, "trend": "NO_DATA"}

        chain_block = point_block(ctv)
        dex_block = flow_block(dex)
        stable_block = point_block(stable)
        fees_block = flow_block(fees)
        protocol_block = protocol_tvl_block(psnap)
        protocol_fee_block = protocol_fees_block(pfees)

        long_votes = [metrics[m]["change_30d_pct"] for m in METRICS]
        tactical_votes = [metrics[m]["change_7d_pct"] for m in METRICS]

        if meta["profile"] == "CHAIN_L1":
            long_votes += [chain_block["change_30d_pct"], dex_block["change_30d_vs_prev30_pct"], stable_block["change_30d_pct"], fees_block["change_30d_vs_prev30_pct"]]
            tactical_votes += [chain_block["change_7d_pct"], dex_block["change_7d_vs_prev7_pct"], stable_block["change_7d_pct"], fees_block["change_7d_vs_prev7_pct"]]
            possible = 7
            available = sum(metrics[m]["latest"] is not None for m in METRICS) + sum([
                chain_block["latest_usd"] is not None,
                dex_block["latest_daily_usd"] is not None,
                stable_block["latest_usd"] is not None,
                fees_block["latest_daily_usd"] is not None,
            ])
        elif meta["profile"] == "RWA_PROTOCOL":
            long_votes += [protocol_block["change_30d_pct"], protocol_fee_block["change_30d_vs_prev30_pct"]]
            tactical_votes += [protocol_block["change_7d_pct"], protocol_fee_block["change_7d_vs_prev7_pct"]]
            possible = 5
            available = sum(metrics[m]["latest"] is not None for m in METRICS) + sum([
                protocol_block["latest_usd"] is not None,
                protocol_fee_block["fees_30d_usd"] is not None,
            ])
        else:
            possible = 3
            available = sum(metrics[m]["latest"] is not None for m in METRICS)

        lc = context(long_votes)
        tc = context(tactical_votes)
        coverage = round(available / possible * 100) if possible else 0
        directional_votes = max(lc["votes"], tc["votes"])
        quality = "TRUSTED" if coverage >= 40 and directional_votes >= 2 else "PARTIAL" if coverage > 0 else "NO_DATA"

        asset = {
            "symbol": sym,
            "metric_profile": meta["profile"],
            "coverage_pct": coverage,
            "directional_votes": directional_votes,
            "quality_gate": quality,
            "source_status": {
                "coinmetrics": cm_status,
                "defillama_chain_tvl": ctv_status,
                "defillama_dex": dex_status,
                "defillama_stablecoins": stable_status,
                "defillama_chain_fees": fees_status,
                "defillama_protocol": psnap_status,
                "defillama_protocol_fees": pfees_status,
            },
            "network_metrics": metrics,
            "chain_tvl": chain_block,
            "dex_volume": dex_block,
            "stablecoin_liquidity": stable_block,
            "chain_fees": fees_block,
            "protocol_tvl": protocol_block,
            "protocol_fees": protocol_fee_block,
            "long_onchain_score_0_10": lc["score"] if quality == "TRUSTED" else None,
            "long_onchain_label": lc["label"] if quality == "TRUSTED" else "INSUFFICIENT_QUALITY",
            "tactical_onchain_score_0_10": tc["score"] if quality == "TRUSTED" else None,
            "tactical_onchain_label": tc["label"] if quality == "TRUSTED" else "INSUFFICIENT_QUALITY",
            "role": "context only; never standalone trade signal",
        }
        assets.append(asset)

        raw_rows.append({
            "date": end.date().isoformat(),
            "symbol": sym,
            "metric_profile": meta["profile"],
            "coverage_pct": coverage,
            "directional_votes": directional_votes,
            "quality_gate": quality,
            "active_addresses": metrics["AdrActCnt"]["latest"],
            "active_addresses_7d_pct": metrics["AdrActCnt"]["change_7d_pct"],
            "active_addresses_30d_pct": metrics["AdrActCnt"]["change_30d_pct"],
            "tx_count": metrics["TxCnt"]["latest"],
            "tx_count_7d_pct": metrics["TxCnt"]["change_7d_pct"],
            "tx_count_30d_pct": metrics["TxCnt"]["change_30d_pct"],
            "transfer_value_adj_usd": metrics["TxTfrValAdjUSD"]["latest"],
            "transfer_value_7d_pct": metrics["TxTfrValAdjUSD"]["change_7d_pct"],
            "transfer_value_30d_pct": metrics["TxTfrValAdjUSD"]["change_30d_pct"],
            "chain_tvl_usd": chain_block["latest_usd"],
            "chain_tvl_7d_pct": chain_block["change_7d_pct"],
            "chain_tvl_30d_pct": chain_block["change_30d_pct"],
            "dex_daily_usd": dex_block["latest_daily_usd"],
            "dex_7d_vs_prev7_pct": dex_block["change_7d_vs_prev7_pct"],
            "dex_30d_vs_prev30_pct": dex_block["change_30d_vs_prev30_pct"],
            "stablecoin_mcap_usd": stable_block["latest_usd"],
            "stablecoin_7d_pct": stable_block["change_7d_pct"],
            "stablecoin_30d_pct": stable_block["change_30d_pct"],
            "chain_fees_daily_usd": fees_block["latest_daily_usd"],
            "chain_fees_7d_vs_prev7_pct": fees_block["change_7d_vs_prev7_pct"],
            "chain_fees_30d_vs_prev30_pct": fees_block["change_30d_vs_prev30_pct"],
            "protocol_tvl_usd": protocol_block["latest_usd"],
            "protocol_tvl_7d_pct": protocol_block["change_7d_pct"],
            "protocol_tvl_30d_pct": protocol_block["change_30d_pct"],
            "protocol_tvl_quality": protocol_block.get("quality"),
            "protocol_fees_30d_usd": protocol_fee_block["fees_30d_usd"],
            "protocol_fees_7d_vs_prev7_pct": protocol_fee_block["change_7d_vs_prev7_pct"],
            "protocol_fees_30d_vs_prev30_pct": protocol_fee_block["change_30d_vs_prev30_pct"],
            "long_onchain_score_0_10": asset["long_onchain_score_0_10"],
            "long_onchain_label": asset["long_onchain_label"],
            "tactical_onchain_score_0_10": asset["tactical_onchain_score_0_10"],
            "tactical_onchain_label": asset["tactical_onchain_label"],
        })
        time.sleep(0.2)

    source_health = {
        "coinmetrics_assets_ok": sum(a["source_status"]["coinmetrics"] == "OK" for a in assets),
        "chain_tvl_assets_ok": sum(a["source_status"]["defillama_chain_tvl"] == "OK" for a in assets),
        "dex_assets_ok": sum(a["source_status"]["defillama_dex"] == "OK" for a in assets),
        "stablecoin_assets_ok": sum(a["source_status"]["defillama_stablecoins"] == "OK" for a in assets),
        "chain_fees_assets_ok": sum(a["source_status"]["defillama_chain_fees"] == "OK" for a in assets),
        "protocol_assets_ok": sum(a["source_status"]["defillama_protocol"] == "OK" for a in assets),
        "protocol_fees_assets_ok": sum(a["source_status"]["defillama_protocol_fees"] == "OK" for a in assets),
    }

    payload = {
        "generated_at_utc": end.isoformat(),
        "engine": "ONCHAIN_ACTIVITY_v0.6",
        "assets": assets,
        "summary": {
            "assets_requested": len(assets),
            "assets_with_any_data": sum(a["coverage_pct"] > 0 for a in assets),
            "trusted_assets": sum(a["quality_gate"] == "TRUSTED" for a in assets),
            "source_health": source_health,
            "layers": ["NETWORK_ACTIVITY", "CHAIN_TVL", "DEX_VOLUME", "STABLECOIN_LIQUIDITY", "CHAIN_FEES", "PROTOCOL_TVL", "PROTOCOL_FEES"],
        },
        "hard_rules": {
            "onchain_is_context_not_signal": True,
            "missing_data_is_never_imputed": True,
            "network_metrics_not_equal_token_fundamentals": True,
            "score_requires_min_40pct_coverage": True,
            "score_requires_min_2_directional_votes": True,
            "ondo_protocol_tvl_requires_exact_or_rwa_match_and_min_10m_usd": True,
            "exchange_netflow_not_claimed_without_verified_source": True,
            "whale_flow_not_claimed_without_verified_source": True,
            "V7_UNTOUCHED": True,
        },
        "limitations": [
            "Coin Metrics community time-series may be unavailable from GitHub runners; source errors remain visible.",
            "Stablecoin liquidity and chain fees are network-level context for ETH/SOL, not token-specific order flow.",
            "ONDO project metrics reject tiny ambiguous protocol matches and require a quality gate.",
            "LINK project-specific directional history remains pending; no proxy is fabricated.",
            "Verified exchange netflow and whale-wallet flow remain pending until a reliable source is connected.",
        ],
    }

    (OUT / "ONCHAIN_ACTIVITY.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    current = pd.DataFrame(raw_rows)
    current.to_csv(OUT / "ONCHAIN_ACTIVITY.csv", index=False)
    history_path = OUT / "ONCHAIN_ACTIVITY_HISTORY.csv"
    combined = current
    if history_path.exists() and not current.empty:
        old = pd.read_csv(history_path)
        combined = pd.concat([old, current], ignore_index=True, sort=False).drop_duplicates(["date", "symbol"], keep="last").sort_values(["date", "symbol"])
    combined.to_csv(history_path, index=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
