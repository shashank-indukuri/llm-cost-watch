#!/usr/bin/env python3
"""Fetch read-only provider cost and usage summaries as JSON for a routine run."""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def get_page(url, headers):
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, json.loads(response.read().decode("utf-8")), None
    except urllib.error.HTTPError as exc:
        # Do not print provider response bodies; they may contain account data.
        return exc.code, None, None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return None, None, type(exc).__name__


def fetch_all(base_url, params, headers, cursor_name):
    rows = []
    buckets = []
    cursor = None
    for _ in range(100):
        query = dict(params)
        if cursor:
            query[cursor_name] = cursor
        url = f"{base_url}?{urllib.parse.urlencode(query, doseq=True)}"
        status, payload, error = get_page(url, headers)
        if status != 200:
            return None, f"HTTP {status}" if status is not None else f"request failed ({error})"
        page_buckets = payload.get("data", [])
        if not isinstance(page_buckets, list):
            return None, "unexpected response shape"
        buckets.extend(page_buckets)
        for bucket in page_buckets:
            if isinstance(bucket, dict):
                result = bucket.get("results", [])
                if isinstance(result, list):
                    rows.extend(result)
        if not payload.get("has_more"):
            return {"buckets": buckets, "rows": rows}, None
        cursor = payload.get("next_page")
        if not cursor:
            return None, "pagination indicated more data but supplied no cursor"
    return None, "stopped after 100 pages to prevent an unbounded run"


def date_bounds(end_date, days):
    last_day = dt.date.fromisoformat(end_date)
    first_day = last_day - dt.timedelta(days=days - 1)
    start = dt.datetime.combine(first_day, dt.time.min, tzinfo=dt.timezone.utc)
    end = dt.datetime.combine(last_day + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)
    return first_day.isoformat(), last_day.isoformat(), start, end


def compact_openai_cost(data):
    total = 0.0
    by_line_item = {}
    currency = "USD"
    for bucket in data["buckets"]:
        for result in bucket.get("results", []) if isinstance(bucket, dict) else []:
            amount = result.get("amount", {})
            value = float(amount.get("value", 0) or 0)
            currency = amount.get("currency", currency)
            total += value
            key = result.get("line_item") or "unattributed"
            by_line_item[key] = by_line_item.get(key, 0.0) + value
    return {"reported_total": round(total, 8), "currency": currency,
            "by_line_item": dict(sorted(by_line_item.items())),
            "bucket_count": len(data["buckets"])}


def compact_openai_usage(data):
    by_model = {}
    for row in data["rows"]:
        model = row.get("model") or "unattributed"
        item = by_model.setdefault(model, {"input_tokens": 0, "output_tokens": 0, "requests": 0})
        item["input_tokens"] += int(row.get("input_tokens", 0) or 0)
        item["output_tokens"] += int(row.get("output_tokens", 0) or 0)
        item["requests"] += int(row.get("num_model_requests", 0) or 0)
    return {"by_model": dict(sorted(by_model.items())), "bucket_count": len(data["buckets"])}


def compact_anthropic_cost(data):
    total = 0.0
    by_model = {}
    currency = "USD"
    for row in data["rows"]:
        amount = float(row.get("amount", 0) or 0)
        currency = row.get("currency", currency)
        total += amount
        model = row.get("model") or row.get("description") or row.get("cost_type") or "unattributed"
        by_model[model] = by_model.get(model, 0.0) + amount
    return {"reported_total": round(total, 8), "currency": currency,
            "by_model_or_line_item": {key: round(value, 8) for key, value in sorted(by_model.items())},
            "bucket_count": len(data["buckets"])}


def compact_anthropic_usage(data):
    by_model = {}
    for row in data["rows"]:
        model = row.get("model") or "unattributed"
        item = by_model.setdefault(model, {"uncached_input_tokens": 0, "cache_read_input_tokens": 0,
                                           "cache_creation_input_tokens": 0, "output_tokens": 0})
        item["uncached_input_tokens"] += int(row.get("uncached_input_tokens", 0) or 0)
        item["cache_read_input_tokens"] += int(row.get("cache_read_input_tokens", 0) or 0)
        item["output_tokens"] += int(row.get("output_tokens", 0) or 0)
        cache = row.get("cache_creation", {})
        if isinstance(cache, dict):
            item["cache_creation_input_tokens"] += sum(int(v or 0) for v in cache.values() if isinstance(v, (int, float)))
    return {"by_model": dict(sorted(by_model.items())), "bucket_count": len(data["buckets"])}


def provider_report(provider, start, end, days):
    if provider == "openai":
        key = os.environ.get("OPENAI_ADMIN_KEY")
        if not key:
            return {"status": "skipped", "reason": "OPENAI_ADMIN_KEY is not configured"}
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        start_ts, end_ts = int(start.timestamp()), int(end.timestamp())
        cost, err = fetch_all("https://api.openai.com/v1/organization/costs",
                              {"start_time": start_ts, "end_time": end_ts, "bucket_width": "1d", "limit": min(days, 180), "group_by": "line_item"}, headers, "page")
        if err:
            return {"status": "error", "endpoint": "organization costs", "detail": err}
        usage, err = fetch_all("https://api.openai.com/v1/organization/usage/completions",
                               {"start_time": start_ts, "end_time": end_ts, "bucket_width": "1d", "limit": min(days, 180), "group_by": "model"}, headers, "page")
        if err:
            return {"status": "partial", "cost": compact_openai_cost(cost), "usage_error": err}
        return {"status": "ok", "cost": compact_openai_cost(cost), "usage": compact_openai_usage(usage)}

    key = os.environ.get("ANTHROPIC_ADMIN_KEY")
    if not key:
        return {"status": "skipped", "reason": "ANTHROPIC_ADMIN_KEY is not configured"}
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    start_text, end_text = start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")
    cost, err = fetch_all("https://api.anthropic.com/v1/organizations/cost_report",
                          {"starting_at": start_text, "ending_at": end_text, "bucket_width": "1d", "limit": min(days, 31)}, headers, "page")
    if err:
        return {"status": "error", "endpoint": "organization cost report", "detail": err}
    usage, err = fetch_all("https://api.anthropic.com/v1/organizations/usage_report/messages",
                           {"starting_at": start_text, "ending_at": end_text, "bucket_width": "1d", "limit": min(days, 31), "group_by[]": "model"}, headers, "page")
    if err:
        return {"status": "partial", "cost": compact_anthropic_cost(cost), "usage_error": err}
    return {"status": "ok", "cost": compact_anthropic_cost(cost), "usage": compact_anthropic_usage(usage)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("both", "openai", "anthropic"), default="both")
    parser.add_argument("--days", type=int, default=7, help="UTC days to summarize (max 180 OpenAI; max 31 Anthropic).")
    parser.add_argument("--end-date", default=(dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=3)).isoformat(),
                        help="Last UTC date to include; defaults to three days ago to allow reporting delay.")
    args = parser.parse_args()
    maximum = 180 if args.provider == "openai" else 31 if args.provider == "anthropic" else 31
    if not 1 <= args.days <= maximum:
        parser.error(f"--days must be between 1 and {maximum} for this provider selection")
    try:
        first_day, last_day, start, end = date_bounds(args.end_date, args.days)
    except ValueError as exc:
        parser.error(f"invalid --end-date: {exc}")

    providers = ("openai", "anthropic") if args.provider == "both" else (args.provider,)
    report = {"window_utc": {"start_date": first_day, "end_date": last_day}, "providers": {}}
    for name in providers:
        report["providers"][name] = provider_report(name, start, end, args.days)
    print(json.dumps(report, indent=2, sort_keys=True))
    states = [item["status"] for item in report["providers"].values()]
    if all(state == "skipped" for state in states) or any(state in ("error", "partial") for state in states):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
