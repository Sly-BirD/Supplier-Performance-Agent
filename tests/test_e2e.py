"""
Comprehensive end-to-end test for the Supplier Performance Agent.

Tests:
  1. Upload CSV file via /api/upload
  2. Fetch all scorecards via /api/scorecards
  3. Fetch individual scorecard via /api/scorecards/{id}
  4. Fetch alerts via /api/alerts
  5. Acknowledge an alert via /api/alerts/{id}/acknowledge
  6. Chat with the agent via /api/chat
  7. Seed sample data via /api/seed
"""

import asyncio
import json
import sys
import os
import time
from pathlib import Path

# Fix Windows console encoding for emoji/unicode
if sys.platform == "win32":
    os.system("")  # enables ANSI escape codes
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx

BASE_URL = "http://127.0.0.1:8000/api"
CSV_PATH = Path(__file__).parent / "test_sample_data.csv"

# Tracking results
results: list[dict] = []


def record(test_name: str, passed: bool, details: str = "", data: object = None):
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({"test": test_name, "passed": passed, "details": details})
    print(f"\n{'='*60}")
    print(f"  {status}  |  {test_name}")
    if details:
        print(f"  Details: {details}")
    if data and not passed:
        print(f"  Response: {json.dumps(data, indent=2, default=str)[:500]}")
    print(f"{'='*60}")


async def main():
    print("\n" + "🚀" * 20)
    print("  SUPPLIER PERFORMANCE AGENT — END-TO-END TEST SUITE")
    print("🚀" * 20 + "\n")

    async with httpx.AsyncClient(timeout=60.0) as client:

        # ── Test 0: Health check ──
        print("\n📋 Test 0: API Health Check")
        try:
            r = await client.get(f"{BASE_URL}/../docs")
            record("API Health Check", r.status_code == 200,
                   f"Status: {r.status_code}")
        except Exception as e:
            record("API Health Check", False, f"Server unreachable: {e}")
            print("\n⚠️  Backend server is not running. Aborting tests.")
            sys.exit(1)

        # ── Test 1: Upload CSV file ──
        print("\n📋 Test 1: File Upload (CSV)")
        try:
            with open(CSV_PATH, "rb") as f:
                files = {"file": ("test_sample_data.csv", f, "text/csv")}
                r = await client.post(f"{BASE_URL}/upload", files=files)
            data = r.json()
            passed = (
                r.status_code == 200
                and "success" in data.get("message", "").lower()
                or "ingested" in data.get("message", "").lower()
            )
            record(
                "File Upload (CSV)",
                passed,
                f"Status: {r.status_code} | Rows: {data.get('row_count')} | Cols: {data.get('column_count')} | Message: {data.get('message', '')[:100]}",
                data,
            )
        except Exception as e:
            record("File Upload (CSV)", False, f"Exception: {e}")

        # ── Test 2: Fetch all scorecards ──
        print("\n📋 Test 2: Fetch All Scorecards")
        try:
            r = await client.get(f"{BASE_URL}/scorecards")
            data = r.json()
            has_scores = any(s.get("composite_score") is not None for s in data)
            record(
                "Fetch All Scorecards",
                r.status_code == 200 and len(data) > 0 and has_scores,
                f"Status: {r.status_code} | Count: {len(data)} | Has scores: {has_scores}",
                data[:3] if data else data,
            )
            # Store for later tests
            scorecards = data
        except Exception as e:
            record("Fetch All Scorecards", False, f"Exception: {e}")
            scorecards = []

        # ── Test 3: Fetch individual scorecard ──
        print("\n📋 Test 3: Fetch Individual Scorecard")
        if scorecards:
            try:
                sup_id = scorecards[0]["supplier_id"]
                r = await client.get(f"{BASE_URL}/scorecards/{sup_id}")
                data = r.json()
                has_dims = bool(data.get("dimensions"))
                record(
                    "Fetch Individual Scorecard",
                    r.status_code == 200 and data.get("composite_score") is not None,
                    f"Supplier: {data.get('supplier_name')} | Score: {data.get('composite_score'):.1f} | Tier: {data.get('tier')} | Dims: {list(data.get('dimensions', {}).keys())}",
                    data,
                )
            except Exception as e:
                record("Fetch Individual Scorecard", False, f"Exception: {e}")
        else:
            record("Fetch Individual Scorecard", False, "No scorecards available to test")

        # ── Test 4: Scorecard data validation ──
        print("\n📋 Test 4: Scorecard Data Validation")
        try:
            valid = True
            issues = []
            for sc in scorecards:
                score = sc.get("composite_score")
                if score is not None and not (0 <= score <= 100):
                    issues.append(f"{sc['supplier_name']} has out-of-range score: {score}")
                    valid = False
                tier = sc.get("tier")
                if tier and tier not in ["Preferred", "Approved", "Watch", "At-Risk", "Unclassified"]:
                    issues.append(f"{sc['supplier_name']} has unexpected tier: {tier}")
                    valid = False
            record(
                "Scorecard Data Validation",
                valid,
                f"Validated {len(scorecards)} scorecards. Issues: {'; '.join(issues) if issues else 'None'}",
            )
        except Exception as e:
            record("Scorecard Data Validation", False, f"Exception: {e}")

        # ── Test 5: Fetch alerts ──
        print("\n📋 Test 5: Fetch Alerts")
        try:
            r = await client.get(f"{BASE_URL}/alerts")
            data = r.json()
            record(
                "Fetch Alerts",
                r.status_code == 200 and isinstance(data, list),
                f"Status: {r.status_code} | Alert count: {len(data)}",
                data[:3] if data else data,
            )
            alerts = data
        except Exception as e:
            record("Fetch Alerts", False, f"Exception: {e}")
            alerts = []

        # ── Test 6: Filter alerts by severity ──
        print("\n📋 Test 6: Filter Alerts by Severity")
        try:
            r = await client.get(f"{BASE_URL}/alerts", params={"severity": "critical"})
            data = r.json()
            all_critical = all(a.get("severity") == "critical" for a in data) if data else True
            record(
                "Filter Alerts by Severity",
                r.status_code == 200 and all_critical,
                f"Status: {r.status_code} | Critical alerts: {len(data)} | All match: {all_critical}",
            )
        except Exception as e:
            record("Filter Alerts by Severity", False, f"Exception: {e}")

        # ── Test 7: Acknowledge an alert ──
        print("\n📋 Test 7: Acknowledge Alert")
        if alerts:
            try:
                alert_id = alerts[0]["id"]
                r = await client.post(f"{BASE_URL}/alerts/{alert_id}/acknowledge")
                data = r.json()
                record(
                    "Acknowledge Alert",
                    r.status_code == 200 and data.get("status") == "acknowledged",
                    f"Alert ID: {alert_id} | Response: {data}",
                    data,
                )
            except Exception as e:
                record("Acknowledge Alert", False, f"Exception: {e}")
        else:
            record("Acknowledge Alert", False, "No alerts available to acknowledge")

        # ── Test 8: Chat with the agent ──
        print("\n📋 Test 8: Chat — General Greeting")
        try:
            r = await client.post(
                f"{BASE_URL}/chat",
                json={"message": "Hello, who are you and what can you help me with?"},
            )
            data = r.json()
            has_reply = bool(data.get("reply")) and len(data["reply"]) > 20
            record(
                "Chat — General Greeting",
                r.status_code == 200 and has_reply,
                f"Reply length: {len(data.get('reply', ''))} | Preview: {data.get('reply', '')[:150]}...",
                data,
            )
        except Exception as e:
            record("Chat — General Greeting", False, f"Exception: {e}")

        # ── Test 9: Chat — Grounded query ──
        print("\n📋 Test 9: Chat — Data-Grounded Query")
        try:
            r = await client.post(
                f"{BASE_URL}/chat",
                json={"message": "Which supplier currently has the lowest performance score and what issues do they have?"},
            )
            data = r.json()
            reply = data.get("reply", "")
            # Check that the reply references actual data (supplier names, scores, etc.)
            is_grounded = any(
                term.lower() in reply.lower()
                for term in ["score", "supplier", "alert", "delivery", "quality", "pricing"]
            )
            record(
                "Chat — Data-Grounded Query",
                r.status_code == 200 and is_grounded and len(reply) > 50,
                f"Reply length: {len(reply)} | Grounded: {is_grounded} | Preview: {reply[:200]}...",
                data,
            )
        except Exception as e:
            record("Chat — Data-Grounded Query", False, f"Exception: {e}")

        # ── Test 10: Chat — Alert inquiry ──
        print("\n📋 Test 10: Chat — Alert Inquiry")
        try:
            r = await client.post(
                f"{BASE_URL}/chat",
                json={"message": "How many active alerts are there and what are the most critical ones?"},
            )
            data = r.json()
            reply = data.get("reply", "")
            mentions_alerts = "alert" in reply.lower()
            record(
                "Chat — Alert Inquiry",
                r.status_code == 200 and mentions_alerts and len(reply) > 30,
                f"Reply length: {len(reply)} | Mentions alerts: {mentions_alerts} | Preview: {reply[:200]}...",
                data,
            )
        except Exception as e:
            record("Chat — Alert Inquiry", False, f"Exception: {e}")

        # ── Test 11: Seed endpoint ──
        print("\n📋 Test 11: Seed Sample Data")
        try:
            r = await client.post(f"{BASE_URL}/seed")
            data = r.json()
            passed = r.status_code == 200 and "seed" in data.get("message", "").lower()
            record(
                "Seed Sample Data",
                passed,
                f"Status: {r.status_code} | Message: {data.get('message', '')[:150]}",
                data,
            )
        except Exception as e:
            record("Seed Sample Data", False, f"Exception: {e}")

        # ── Test 12: Scorecards after seed (verify new suppliers added) ──
        print("\n📋 Test 12: Scorecards After Seed")
        try:
            r = await client.get(f"{BASE_URL}/scorecards")
            data = r.json()
            supplier_names = [s["supplier_name"] for s in data]
            has_seeded = any("Acme" in n or "Beta" in n or "Gamma" in n for n in supplier_names)
            record(
                "Scorecards After Seed",
                r.status_code == 200 and len(data) >= 5 and has_seeded,
                f"Total suppliers: {len(data)} | Names: {supplier_names[:8]}",
            )
        except Exception as e:
            record("Scorecards After Seed", False, f"Exception: {e}")

        # ── Test 13: Invalid file upload ──
        print("\n📋 Test 13: Invalid File Upload")
        try:
            files = {"file": ("bad_file.json", b'{"not": "csv"}', "application/json")}
            r = await client.post(f"{BASE_URL}/upload", files=files)
            record(
                "Invalid File Upload (Error Handling)",
                r.status_code == 400,
                f"Status: {r.status_code} (expected 400) | Detail: {r.json().get('detail', '')[:100]}",
            )
        except Exception as e:
            record("Invalid File Upload (Error Handling)", False, f"Exception: {e}")

        # ── Test 14: 404 scorecard ──
        print("\n📋 Test 14: Non-existent Scorecard (404)")
        try:
            r = await client.get(f"{BASE_URL}/scorecards/nonexistent-id-12345")
            record(
                "Non-existent Scorecard (404 Handling)",
                r.status_code == 404,
                f"Status: {r.status_code} (expected 404)",
            )
        except Exception as e:
            record("Non-existent Scorecard (404 Handling)", False, f"Exception: {e}")

    # ── Final Report ──
    print("\n\n" + "=" * 70)
    print("  📊  FINAL TEST REPORT")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    print(f"\n  Total Tests: {total}")
    print(f"  ✅ Passed:   {passed}")
    print(f"  ❌ Failed:   {failed}")
    print(f"  Success Rate: {passed / total * 100:.1f}%\n")

    if failed > 0:
        print("  ── Failed Tests ──")
        for r in results:
            if not r["passed"]:
                print(f"    ❌ {r['test']}: {r['details']}")
        print()

    print("  ── All Results ──")
    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"    {status} {r['test']}")

    print("\n" + "=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
