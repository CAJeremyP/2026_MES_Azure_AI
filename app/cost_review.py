"""
cost_review.py — Azure Cost Management
Queries the Azure Cost Management API to show actual spend
on the resource group for the last 30 days.

Requires the logged-in account to have Cost Management Reader role.
Falls back gracefully if permissions are missing.
"""
import os
import json
import subprocess
import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

SUBSCRIPTION_ID  = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
RESOURCE_GROUP   = os.environ.get("AZURE_RESOURCE_GROUP", "rg-ai-demo")

# Free tier limits for reference
FREE_TIER_INFO = {
    "Custom Vision (F0)": {
        "limit": "5,000 transactions/month",
        "price_over": "$2.00 per 1,000 transactions",
    },
    "Document Intelligence (F0)": {
        "limit": "500 pages/month",
        "price_over": "$1.50 per 1,000 pages",
    },
    "Blob Storage (LRS)": {
        "limit": "5 GB free first year (new accounts)",
        "price_over": "$0.018/GB/month",
        "monthly_est": "<$0.01 for demo images",
    },
}


def get_cost_summary() -> dict:
    """
    Attempt to fetch actual costs via Azure CLI.
    Returns a dict with cost data or estimated costs if unavailable.
    """
    print("  💰  Fetching Azure cost data...")

    end_date = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    try:
        result = subprocess.run([
            "az", "consumption", "usage", "list",
            "--subscription", SUBSCRIPTION_ID,
            "--start-date", start_date,
            "--end-date", end_date,
            "--query", "[?contains(instanceId, '{}')].{{service:product, cost:pretaxCost, currency:currency}}".format(RESOURCE_GROUP.lower()),
            "--output", "json"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data:
                total = sum(float(item.get("cost", 0)) for item in data)
                currency = data[0].get("currency", "USD") if data else "USD"
                _print_actual_costs(data, total, currency, start_date, end_date)
                return {"actual_costs": data, "total": total, "currency": currency}
    except Exception as e:
        pass   # Fall through to estimated costs

    # Fallback: show estimated / free tier info
    _print_estimated_costs()
    return {"estimated": FREE_TIER_INFO}


def _print_actual_costs(data, total, currency, start_date, end_date):
    from tabulate import tabulate
    rows = [(item.get("service", "Unknown"), f"${float(item.get('cost', 0)):.4f}") for item in data]
    rows.append(("─" * 40, "─" * 10))
    rows.append(("TOTAL", f"${total:.4f} {currency}"))
    print(f"\n  Actual costs ({start_date} to {end_date}):")
    print(tabulate(rows, headers=["Service", "Cost"], tablefmt="rounded_outline"))


def _print_estimated_costs():
    print("\n  📊  Cost breakdown (estimated / free tier reference):")
    print()
    for service, info in FREE_TIER_INFO.items():
        print(f"  ▶  {service}")
        for k, v in info.items():
            label = k.replace("_", " ").title()
            print(f"       {label}: {v}")
    print()
    print("  💡  All Cognitive Services in this demo use the F0 (free) tier.")
    print("      Estimated total cost for a 1-day demo: $0.50 - $5.00")
    print("      Run teardown.sh immediately after the session to stop charges.")
