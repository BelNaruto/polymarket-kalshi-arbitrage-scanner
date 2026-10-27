#!/usr/bin/env python3
"""Polymarket <-> Kalshi <-> Manifold arbitrage scanner.

Uses the Prediction Markets API on RapidAPI:
https://rapidapi.com/belchiorarkad-FqvHs2EDOtP/api/prediction-markets

Support / faster replies: Telegram @pintoflow
"""
import argparse
import os
import sys
import time

import requests

KEY = os.environ.get("RAPIDAPI_KEY")
HOST = os.environ.get("RAPIDAPI_HOST")  # shown on the API's Endpoints tab


def call(path, **params):
    if not KEY or not HOST:
        sys.exit("Set RAPIDAPI_KEY and RAPIDAPI_HOST (see .env.example)")
    r = requests.get(
        f"https://{HOST}{path}",
        params={k: v for k, v in params.items() if v is not None},
        headers={"x-rapidapi-key": KEY, "x-rapidapi-host": HOST},
        timeout=30,
    )
    body = r.json()
    if body.get("error"):
        raise RuntimeError(body.get("message", "API error"))
    return body["data"]


def cross_venue(args):
    data = call(
        "/api/arbitrage",
        q=args.q,
        minEdge=args.min_edge,
        feeAware=str(args.fee_aware).lower(),
        limit=args.limit,
    )
    rows = data["opportunities"]
    print(f"\nScanned {data['scanned']}  |  {len(rows)} opportunities (edge >= {args.min_edge:.1%})")
    for o in rows:
        legs = " + ".join(f"{b['side']}@{b['venue']} {b['price']:.3f}" for b in o["buy"])
        print(f"  {o['edgePct']:5.2f}%  sim={o['similarity']:.2f}  cost={o['cost']:.3f}  {legs}")
        print(f"         {o['markets'][0]['title']}")


def dutch_book(args):
    data = call("/api/arbitrage/events", q=args.q, minEdge=args.min_edge, feeAware=str(args.fee_aware).lower())
    events = data.get("events") or data.get("opportunities") or data.get("results") or []
    if not events:
        print("No events returned. Raw response keys:", list(data))
    print(f"\n{len(events)} multi-outcome events with a positive field edge")
    for e in events:
        field = e.get("buyTheField", {})
        print(f"  {field.get('edgePct', 0):5.2f}%  {e.get('event', {}).get('title', '?')}  ({e.get('outcomeCount', '?')} legs)")


def main():
    p = argparse.ArgumentParser(description="Scan prediction markets for arbitrage")
    p.add_argument("-q", help="topic filter, e.g. 'bitcoin' (recommended)")
    p.add_argument("--min-edge", type=float, default=0.02, help="minimum edge, 0.02 = 2%%")
    p.add_argument("--fee-aware", action="store_true", help="subtract Kalshi taker fees")
    p.add_argument("--events", action="store_true", help="same-venue dutch-book scan instead")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--watch", type=int, metavar="SECONDS", help="repeat every N seconds")
    args = p.parse_args()
    while True:
        try:
            (dutch_book if args.events else cross_venue)(args)
        except Exception as exc:  # keep watch mode alive on transient 502s
            print("error:", exc)
        if not args.watch:
            break
        time.sleep(max(args.watch, 10))


if __name__ == "__main__":
    main()
