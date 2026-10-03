"""
SI Scout Local Dashboard Application.
Runs locally bound to 127.0.0.1:8501 only.
Zero telemetry, no CDN scripts, 100% offline.
"""

import sys
from pathlib import Path

# Add project root to sys.path so 'ui' and 'si_scout' packages resolve correctly
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from datetime import datetime, timezone
import io
import json
import logging
import os
import queue
import re
import secrets
import subprocess
import threading
from typing import Dict, Optional

from flask import Flask, Response, jsonify, render_template, request, send_file

from ui.data import UIDataManager
from ui.recheck import perform_recheck_batch
from ui.freshness import evaluate_freshness

logger = logging.getLogger(__name__)

# Global concurrency lock and scan process queue
SCAN_LOCK = threading.Lock()
SCAN_RUNNING = False
SCAN_LOG_QUEUE: "queue.Queue[str]" = queue.Queue()

def create_app(test_config: Optional[Dict] = None) -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

    @app.before_request
    def verify_same_origin():
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("Origin")
            referer = request.headers.get("Referer")
            host = request.host
            allowed_prefixes = (f"http://{host}", f"https://{host}", "http://127.0.0.1", "http://localhost")
            if origin and not any(origin.startswith(p) for p in allowed_prefixes):
                return jsonify({"error": "Cross-origin request rejected"}), 403
            if not origin and referer and not any(referer.startswith(p) for p in allowed_prefixes):
                return jsonify({"error": "Cross-origin referer rejected"}), 403

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
        return response

    if test_config:
        app.config.update(test_config)

    is_demo = app.config.get("DEMO", False) or ("--demo" in sys.argv)
    app.config["DEMO"] = is_demo
    if is_demo:
        demo_dir = app.config.get("DEMO_DIR", REPO_ROOT / "demo_data")
        try:
            from scripts.generate_demo_data import ensure_demo_databases
            ensure_demo_databases(demo_dir)
        except Exception as e:
            logger.warning(f"Could not auto-generate demo databases: {e}")

    csv_path = app.config.get("CSV_PATH", Path("results.csv"))
    db_path = app.config.get("DB_PATH", Path("scout.db"))
    portfolio_db_path = app.config.get("PORTFOLIO_DB_PATH", Path("portfolio.db"))
    rationales_path = app.config.get("RATIONALES_PATH", Path("rationales.json"))

    def get_manager() -> UIDataManager:
        return UIDataManager(
            csv_path=csv_path if not is_demo else None,
            db_path=db_path if not is_demo else None,
            portfolio_db_path=portfolio_db_path if not is_demo else None,
            rationales_path=rationales_path if not is_demo else None,
            is_demo=is_demo
        )

    @app.context_processor
    def inject_global_vars():
        return {
            "is_demo": is_demo
        }

    # 1. Overview Screen
    @app.route("/")
    def overview():
        mgr = get_manager()
        stats = mgr.get_overview_stats()
        return render_template("overview.html",
                               active_page="home",
                               overview=stats,
                               stats=stats.get("stats", {}),
                               freshness=stats["freshness"])

    # Budget Lab Screen
    @app.route("/budget")
    def budget_lab():
        mgr = get_manager()
        overview = mgr.get_overview_stats()
        return render_template("budget.html",
                               active_page="budget",
                               freshness=overview["freshness"])

    @app.route("/api/budget/calculate", methods=["POST", "GET"])
    def api_budget_calculate():
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
        else:
            data = request.args.to_dict()
        try:
            budget = float(data.get("budget", 200))
            reserve_pct = float(data.get("reserve_pct", 0))
            first_year = float(data.get("first_year", 12.13))
            renewal = float(data.get("renewal", 13.61))
            tax_pct = float(data.get("tax_pct", 0))
            term_years = int(data.get("term_years", 3))
            domain_count = int(data.get("domain_count", 5))
            annual_sell_through_pct = float(data.get("annual_sell_through_pct", 2.0))
            net_sale_price = float(data.get("net_sale_price", 500))
            currency = str(data.get("currency", "EUR"))
            exchange_rate = float(data.get("exchange_rate", 1.0))
        except (ValueError, TypeError):
            budget = 200.0
            reserve_pct = 0.0
            first_year = 12.13
            renewal = 13.61
            tax_pct = 0.0
            term_years = 3
            domain_count = 5
            annual_sell_through_pct = 2.0
            net_sale_price = 500.0
            currency = "EUR"
            exchange_rate = 1.0

        from si_scout.budget_math import calculate_budget_model
        model = calculate_budget_model(
            budget=budget,
            reserve_pct=reserve_pct,
            first_year=first_year,
            renewal=renewal,
            tax_pct=tax_pct,
            term_years=term_years,
            domain_count=domain_count,
            annual_sell_through_pct=annual_sell_through_pct,
            net_sale_price=net_sale_price,
            currency=currency,
            exchange_rate=exchange_rate,
        )
        return jsonify(model)

    # Name Lab Screen
    @app.route("/name-lab")
    def name_lab():
        mgr = get_manager()
        overview = mgr.get_overview_stats()
        return render_template("name_lab.html",
                               active_page="name_lab",
                               freshness=overview["freshness"])

    @app.route("/api/name-lab/screen", methods=["POST", "GET"])
    def api_name_lab_screen():
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            label = str(data.get("label", ""))
        else:
            label = str(request.args.get("label", ""))
        from si_scout.name_lab import screen_label_offline
        result = screen_label_offline(label)
        return jsonify(result)

    # Funnel Screen
    @app.route("/funnel")
    def funnel_screen():
        mgr = get_manager()
        findings_data = mgr.get_findings_stats()
        overview = mgr.get_overview_stats()
        return render_template("funnel.html",
                               active_page="funnel",
                               findings=findings_data,
                               freshness=overview["freshness"])

    @app.route("/api/funnel/data")
    def api_funnel_data():
        mgr = get_manager()
        findings = mgr.get_findings_stats()
        funnel = findings.get("funnel", {})
        return jsonify({
            "stages": funnel.get("stage_descriptions", []),
            "total_candidates": funnel.get("total_candidates_generated", 0),
            "strict_survivors": funnel.get("strict_survivors", 0),
            "source_file": funnel.get("source_file", "demo_data/findings_data.json"),
            "snapshot_date": funnel.get("generation_date", "2026-10-02"),
        })

    # Gate Simulator Screen
    @app.route("/gates")
    def gate_simulator():
        mgr = get_manager()
        overview = mgr.get_overview_stats()
        return render_template("gates_sim.html",
                               active_page="gates",
                               freshness=overview["freshness"])

    # Story Mode Screen (55s Walkthrough)
    @app.route("/story")
    def story_mode():
        mgr = get_manager()
        overview = mgr.get_overview_stats()
        findings = mgr.get_findings_stats()
        return render_template("story.html",
                               active_page="story",
                               findings=findings,
                               stats=overview.get("stats", {}),
                               freshness=overview["freshness"])


    # Findings Screen (Computed from build data fixtures)
    @app.route("/findings")
    def findings():
        mgr = get_manager()
        findings_data = mgr.get_findings_stats()
        return render_template("findings.html",
                               active_page="findings",
                               findings=findings_data)

    # 2. Candidates Table
    @app.route("/candidates")
    def candidates():
        mgr = get_manager()
        df = mgr.get_candidates_df()
        candidates_list = df.to_dict(orient="records") if not df.empty else []
        overview = mgr.get_overview_stats()
        return render_template("candidates.html",
                               active_page="candidates",
                               candidates=candidates_list,
                               freshness=overview["freshness"])

    # 3. Name Detail Screen
    @app.route("/detail/<domain>")
    def detail(domain: str):
        mgr = get_manager()
        cand_detail = mgr.get_candidate_detail(domain)
        if not cand_detail:
            return "Domain candidate not found", 404
        overview = mgr.get_overview_stats()
        return render_template("detail.html",
                               active_page="candidates",
                               detail=cand_detail,
                               freshness=overview["freshness"])

    # 4. Shortlist & Budget Allocation
    @app.route("/shortlist")
    def shortlist():
        mgr = get_manager()
        shortlist_items = mgr.portfolio.get_shortlist()
        overview = mgr.get_overview_stats()
        budget = overview["budget"]

        # Enrich shortlisted names with candidate details
        shortlisted_names = []
        total_committed = 0.0

        for item in shortlist_items:
            cand_detail = mgr.get_candidate_detail(item["domain"])
            if cand_detail:
                carry = cand_detail.get("carry_3yr_usd", 39.35)
                total_committed += carry
                # Check gate readiness
                is_ready = (
                    cand_detail["rdap_status"] == "AVAILABLE_CANDIDATE" and
                    cand_detail["is_verified_human"] and
                    cand_detail["human_rationale"] and
                    cand_detail["cand_freshness"]["is_all_fresh"]
                )
                cand_detail["is_ready"] = is_ready
                shortlisted_names.append(cand_detail)

        remaining_cash = round(budget["effective_budget"] - total_committed, 2)

        return render_template("shortlist.html",
                               active_page="shortlist",
                               shortlisted_names=shortlisted_names,
                               budget=budget,
                               total_committed=round(total_committed, 2),
                               remaining_cash=remaining_cash,
                               freshness=overview["freshness"])

    # 5. Watch Mode Screen
    @app.route("/watch")
    def watch():
        mgr = get_manager()
        overview = mgr.get_overview_stats()
        # Read diffs from watch_history in scout.db
        diffs = []
        conn = mgr._get_ro_scout_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT domain, old_status, new_status, recorded_utc FROM watch_history ORDER BY id DESC LIMIT 50")
                diffs = [{"domain": r[0], "old_status": r[1], "new_status": r[2], "recorded_utc": r[3]} for r in cursor.fetchall()]
            except Exception:
                pass
            finally:
                conn.close()

        return render_template("watch.html",
                               active_page="watch",
                               diffs=diffs,
                               counter_history=overview.get("counter_history", []),
                               watchlist=mgr.get_watchlist(),
                               watch_log=mgr.get_watch_log(),
                               freshness=overview["freshness"])

    # 5b. Drop Watch Screen
    @app.route("/drop-watch")
    def drop_watch():
        mgr = get_manager()
        overview = mgr.get_overview_stats()
        df = mgr.get_drop_watch_df()
        drop_records = df.to_dict(orient="records") if not df.empty else []
        return render_template("drop_watch.html",
                               active_page="drop_watch",
                               drop_records=drop_records,
                               freshness=overview["freshness"])

    # 5c. Calibration Screen
    @app.route("/calibration")
    def calibration():
        mgr = get_manager()
        overview = mgr.get_overview_stats()
        stats = mgr.get_calibration_stats()
        return render_template("calibration.html",
                               active_page="calibration",
                               stats=stats,
                               overview=overview,
                               freshness=overview["freshness"])

    @app.route("/api/calibration/add", methods=["POST"])
    def api_calibration_add():
        data = request.get_json() or {}
        domain = data.get("domain", "")
        registry_status = data.get("registry_status", "404 Not Found")
        registry_time_utc = data.get("registry_time_utc", datetime.now(timezone.utc).isoformat())
        registry_recheck_time = data.get("registry_recheck_time", "UNKNOWN")
        registrar_name = data.get("registrar_name", "")
        registrar_result = data.get("registrar_result", "available")
        registrar_time_utc = data.get("registrar_time_utc", datetime.now(timezone.utc).isoformat())
        notes = data.get("notes", "")

        mgr = get_manager()
        rec = mgr.add_calibration_record(
            domain=domain,
            registry_status=registry_status,
            registry_time_utc=registry_time_utc,
            registrar_name=registrar_name,
            registrar_result=registrar_result,
            registrar_time_utc=registrar_time_utc,
            notes=notes,
            registry_recheck_time=registry_recheck_time
        )
        # Also sync to registrar_confirmations
        mgr.save_registrar_confirmation(
            domain=domain,
            registrar=registrar_name,
            result=registrar_result,
            checked_utc=registrar_time_utc,
            notes=notes
        )
        return jsonify({"success": True, "record": rec})

    @app.route("/api/confirm-checkout", methods=["POST"])
    def api_confirm_checkout():
        data = request.get_json() or {}
        domain = data.get("domain", "")
        registrar = data.get("registrar", "")
        result = data.get("result", "")
        checked_utc = data.get("checked_utc", datetime.now(timezone.utc).isoformat())
        notes = data.get("notes", "")

        mgr = get_manager()
        is_valid, msg = mgr.save_registrar_confirmation(
            domain=domain,
            registrar=registrar,
            result=result,
            checked_utc=checked_utc,
            notes=notes
        )
        # Also record to calibration
        cand = mgr.get_candidate_detail(domain)
        reg_status = cand.get("rdap_status", "UNKNOWN") if cand else "UNKNOWN"
        reg_time = cand.get("checked_utc", checked_utc) if cand else checked_utc
        mgr.add_calibration_record(
            domain=domain,
            registry_status=reg_status,
            registry_time_utc=reg_time,
            registrar_name=registrar,
            registrar_result=result,
            registrar_time_utc=checked_utc,
            notes=f"checkout modal: {notes}"
        )
        return jsonify({"success": True, "is_valid": is_valid, "message": msg})

    # 6. Scan Control Screen
    @app.route("/scan")
    def scan():
        mgr = get_manager()
        overview = mgr.get_overview_stats()
        return render_template("scan.html",
                               active_page="scan",
                               freshness=overview["freshness"])

    # 7. Portfolio & Outreach Screen
    @app.route("/portfolio")
    def portfolio():
        mgr = get_manager()
        items = mgr.portfolio.get_portfolio_items()
        outreach = mgr.portfolio.get_outreach_log()
        kill_criteria = mgr.portfolio.get_kill_criteria()
        overview = mgr.get_overview_stats()
        return render_template("portfolio.html",
                               active_page="portfolio",
                               items=items,
                               outreach=outreach,
                               kill_criteria=kill_criteria,
                               freshness=overview["freshness"])

    # 8. Glossary & Limitations Screen
    @app.route("/glossary")
    def glossary():
        mgr = get_manager()
        limitations_text = mgr.get_limitations_markdown()
        overview = mgr.get_overview_stats()
        return render_template("glossary.html",
                               active_page="glossary",
                               limitations_text=limitations_text,
                               freshness=overview["freshness"])

    # API Endpoints
    @app.route("/api/shortlist/toggle", methods=["POST"])
    def api_shortlist_toggle():
        data = request.get_json() or {}
        domain = data.get("domain", "")
        if not domain:
            return jsonify({"error": "Domain required"}), 400
        mgr = get_manager()
        is_shortlisted = mgr.portfolio.toggle_shortlist(domain)
        return jsonify({"success": True, "domain": domain, "is_shortlisted": is_shortlisted})

    @app.route("/api/rationale/save", methods=["POST"])
    def api_rationale_save():
        data = request.get_json() or {}
        label = data.get("label", "")
        rationale = data.get("rationale", "")
        verified = bool(data.get("verified_checkbox", False))
        mgr = get_manager()
        success, msg = mgr.save_human_rationale(label, rationale, verified)
        if success:
            return jsonify({"success": True, "message": msg})
        else:
            return jsonify({"success": False, "error": msg}), 400

    @app.route("/api/recheck", methods=["POST"])
    def api_recheck():
        if is_demo:
            return jsonify({"success": False, "error": "Recheck disabled in demo mode. Running offline with synthetic fixtures."}), 400
        data = request.get_json() or {}
        domains = data.get("domains", [])
        if not domains:
            return jsonify({"error": "No domains provided"}), 400
        try:
            results = perform_recheck_batch(domains, db_path=db_path, max_allowed=25)
            return jsonify({"success": True, "results": results})
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/watch/run", methods=["POST"])
    def api_watch_run():
        if is_demo:
            return jsonify({"success": False, "error": "Live watch disabled in demo mode. Running offline with synthetic fixtures."}), 400
        from si_scout.watch import WatchEngine
        watch_engine = WatchEngine(db_path=db_path)
        snapshot = watch_engine.fetch_and_record_counters()
        output = "No snapshot"
        if snapshot:
            output = f"Recorded snapshot for {snapshot.snapshot_date}: Total {snapshot.total_domains:,} domains, {snapshot.domains_last_24h:,} in 24h."
        return jsonify({"success": True, "output": output})

    @app.route("/api/scan/start", methods=["POST"])
    def api_scan_start():
        if is_demo:
            return jsonify({"success": False, "error": "Scanning disabled in demo mode. Running offline with synthetic fixtures."}), 400
        global SCAN_RUNNING, SCAN_LOG_QUEUE
        with SCAN_LOCK:
            if SCAN_RUNNING:
                return jsonify({"success": False, "error": "A scan is already running. Please wait for completion."}), 400
            SCAN_RUNNING = True

        data = request.get_json() or {}
        try:
            raw_top = int(data.get("top", 20))
        except (ValueError, TypeError):
            raw_top = 20
        top = max(1, min(raw_top, 100))
        extra = str(data.get("extra", "")).strip()
        if extra and not re.match(r'^[a-z0-9,\-]+$', extra):
            with SCAN_LOCK:
                SCAN_RUNNING = False
            return jsonify({"success": False, "error": "Invalid characters in extra names. Allowed: a-z, 0-9, hyphen, comma."}), 400
        skip_twins = bool(data.get("skip_twins", True))

        script_path = str((REPO_ROOT / "si_agent.py").resolve())
        cmd = [sys.executable, script_path, "--top", str(top)]
        if extra:
            cmd.extend(["--extra", extra])
        if skip_twins:
            cmd.append("--skip-twins")

        def run_subprocess():
            global SCAN_RUNNING
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        SCAN_LOG_QUEUE.put(line.strip())
                    proc.stdout.close()
                proc.wait()
            except Exception as e:
                SCAN_LOG_QUEUE.put(f"Scan error: {str(e)}")
            finally:
                SCAN_LOG_QUEUE.put("[DONE]")
                with SCAN_LOCK:
                    SCAN_RUNNING = False

        threading.Thread(target=run_subprocess, daemon=True).start()
        return jsonify({"success": True, "message": "Scan started"})

    @app.route("/api/scan/stream")
    def api_scan_stream():
        def generate():
            while True:
                try:
                    line = SCAN_LOG_QUEUE.get(timeout=20.0)
                    yield f"data: {line}\n\n"
                    if line == "[DONE]":
                        break
                except queue.Empty:
                    yield ": keep-alive\n\n"
        return Response(generate(), mimetype="text/event-stream")

    @app.route("/api/portfolio/add", methods=["POST"])
    def api_portfolio_add():
        data = request.get_json() or {}
        domain = data.get("domain", "")
        date = data.get("purchase_date", "")
        price = float(data.get("price_paid", 0.0))
        registrar = data.get("registrar", "Dynadot")
        mgr = get_manager()
        mgr.portfolio.add_portfolio_item(domain=domain, purchase_date=date, price_paid=price, registrar=registrar)
        return jsonify({"success": True})

    @app.route("/api/outreach/add", methods=["POST"])
    def api_outreach_add():
        data = request.get_json() or {}
        mgr = get_manager()
        mgr.portfolio.add_outreach(
            company=data.get("company", ""),
            contact_person=data.get("contact_person", ""),
            date_contacted=data.get("date_contacted", ""),
            reply_status="PENDING",
            notes=data.get("notes", "")
        )
        return jsonify({"success": True})

    @app.route("/api/portfolio/kill-criteria", methods=["POST"])
    def api_kill_criteria():
        data = request.get_json() or {}
        mgr = get_manager()
        mgr.portfolio.update_kill_criteria(data.get("contract_text", ""))
        return jsonify({"success": True})

    @app.route("/api/export/csv")
    @app.route("/api/candidates/export/csv")
    def api_export_csv():
        mgr = get_manager()
        df = mgr.get_candidates_df()
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return send_file(
            io.BytesIO(buf.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"si_scout_candidates_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
        )

    @app.route("/api/shortlist/export/markdown")
    def api_export_shortlist_md():
        mgr = get_manager()
        shortlist_items = mgr.portfolio.get_shortlist()
        lines = [
            "# SI Scout: Final Candidate Shortlist",
            f"**Exported**: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`",
            "",
            "| Domain | 1-Yr Cost | 3-Yr Carry | Registrar | Human Rationale | Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ]
        for s in shortlist_items:
            det = mgr.get_candidate_detail(s["domain"])
            if det:
                lines.append(
                    f"| **{det['domain']}** | ${det['year1_usd']:.2f} | ${det['carry_3yr_usd']:.2f} | {det['cheapest_registrar']} | {det['human_rationale'] or 'N/A'} | {det['rdap_status']} |"
                )
        lines.extend([
            "",
            "---",
            "> **Disclaimer**: High screening scores indicate passing heuristics, not expected market value.",
            "> All purchases must be made manually. Confirm premium/reserved status at registrar checkout."
        ])
        md_bytes = "\n".join(lines).encode("utf-8")
        return send_file(
            io.BytesIO(md_bytes),
            mimetype="text/markdown",
            as_attachment=True,
            download_name="shortlist.md"
        )

    return app

def main():
    is_demo = "--demo" in sys.argv
    port = 8501
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                pass
    if "PORT" in os.environ:
        try:
            port = int(os.environ["PORT"])
        except ValueError:
            pass

    app = create_app({"DEMO": is_demo})
    print("================================================================================")
    if is_demo:
        print("          SI SCOUT LOCAL DASHBOARD (DEMO MODE - OFFLINE SYNTHETIC)            ")
    else:
        print("              SI SCOUT LOCAL DASHBOARD (Offline-First Workbench)               ")
    print("================================================================================")
    print(f"Binding strictly to: http://127.0.0.1:{port}")
    print("Zero telemetry, zero CDN scripts, 100% private.")
    if is_demo:
        print("Active: Demo fixtures in demo_data/ (Zero live network lookups)")
    print("Press Ctrl+C to stop.")
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    main()
