"""
Data Access Layer for SI Scout UI.
Reads all repository sources in read-only mode, handles missing/empty files gracefully,
and exposes typed methods.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import yaml

from si_scout.config import load_registrars, load_config, RegistrarInfo
from ui.portfolio_store import PortfolioStore
from ui.freshness import evaluate_freshness

logger = logging.getLogger(__name__)

class UIDataManager:
    def __init__(self,
                 csv_path: Optional[Path] = None,
                 db_path: Optional[Path] = None,
                 portfolio_db_path: Optional[Path] = None,
                 rationales_path: Optional[Path] = None,
                 registrars_path: Optional[Path] = None,
                 limitations_path: Optional[Path] = None,
                 is_demo: bool = False,
                 demo_dir: Optional[Path] = None):
        self.is_demo = is_demo
        self.demo_dir = demo_dir or Path("demo_data")

        if is_demo:
            self.csv_path = csv_path or (self.demo_dir / "results.csv")
            self.db_path = db_path or (self.demo_dir / "scout.db")
            self.portfolio_db_path = portfolio_db_path or (self.demo_dir / "portfolio.db")
            if not self.db_path.exists() or not self.portfolio_db_path.exists():
                try:
                    from scripts.generate_demo_data import ensure_demo_databases
                    ensure_demo_databases(self.demo_dir)
                except Exception as e:
                    logger.warning(f"Could not auto-generate demo databases: {e}")
            self.rationales_path = rationales_path or (self.demo_dir / "rationales.json")
            self.confirmations_path = self.demo_dir / "registrar_confirmations.json"
            self.calibration_path = self.demo_dir / "calibration.json"
            self.drop_watch_path = self.demo_dir / "drop_watch.csv"
            self.watch_log_path = self.demo_dir / "watch_log.csv"
            self.findings_path = self.demo_dir / "findings_data.json"
        else:
            self.csv_path = csv_path or Path("results.csv")
            self.db_path = db_path or Path("scout.db")
            self.portfolio_db_path = portfolio_db_path or Path("portfolio.db")
            self.rationales_path = rationales_path or Path("rationales.json")
            self.confirmations_path = Path("registrar_confirmations.json")
            self.calibration_path = Path("calibration.json")
            self.drop_watch_path = Path("drop_watch.csv")
            self.watch_log_path = Path("watch_log.csv")
            self.findings_path = Path("demo_data/findings_data.json")

        self.registrars_path = registrars_path or Path("si_scout/registrars.yaml")
        self.limitations_path = limitations_path or Path("LIMITATIONS.md")
        self.portfolio = PortfolioStore(self.portfolio_db_path)

    def _get_ro_scout_conn(self) -> Optional[sqlite3.Connection]:
        if not self.db_path.exists():
            return None
        try:
            # Read-only URI
            uri = f"file:{self.db_path.resolve().as_posix()}?mode=ro"
            return sqlite3.connect(uri, uri=True)
        except Exception:
            try:
                return sqlite3.connect(self.db_path)
            except Exception as e:
                logger.error(f"Cannot open scout.db: {e}")
                return None

    def get_candidates_df(self) -> pd.DataFrame:
        """Reads results.csv safely and merges with shortlist state."""
        if not self.csv_path.exists():
            return pd.DataFrame()
        try:
            df = pd.read_csv(self.csv_path, dtype=str)
            if df.empty or "domain" not in df.columns:
                return pd.DataFrame()

            # Ensure numeric columns
            if "total_score" in df.columns:
                df["total_score"] = pd.to_numeric(df["total_score"], errors="coerce").fillna(0.0)
            if "year1_usd" in df.columns:
                df["year1_usd"] = pd.to_numeric(df["year1_usd"], errors="coerce").fillna(0.0)
            if "carry_3yr_usd" in df.columns:
                df["carry_3yr_usd"] = pd.to_numeric(df["carry_3yr_usd"], errors="coerce").fillna(0.0)

            # Add domain length
            df["length"] = df["label"].apply(lambda x: len(str(x)) if pd.notna(x) else 0)

            # Add shortlisted flag
            shortlist_domains = {s["domain"] for s in self.portfolio.get_shortlist()}
            df["is_shortlisted"] = df["domain"].apply(lambda d: d in shortlist_domains)

            return df
        except Exception as e:
            logger.error(f"Error reading results.csv: {e}")
            return pd.DataFrame()

    def get_overview_stats(self) -> Dict[str, Any]:
        """Calculates budget model, scan tallies, status counts, and counter history."""
        # Registrars & Budget
        try:
            registrars = load_registrars(self.registrars_path)
        except Exception:
            registrars = {}

        cheap_reg = min(registrars.values(), key=lambda r: r.carry_3yr) if registrars else None
        carry_3yr = cheap_reg.carry_3yr if cheap_reg else 39.35
        eff_budget = 180.0
        max_names = int(eff_budget // carry_3yr) if carry_3yr > 0 else 4

        df = self.get_candidates_df()
        has_data = not df.empty

        status_counts = {
            "AVAILABLE_CANDIDATE": 0,
            "REGISTERED": 0,
            "QUARANTINE/PENDING_DELETE": 0,
            "RESERVED": 0,
            "UNCERTAIN": 0
        }
        tier_counts = {
            "BUY_CANDIDATE": 0,
            "MONITOR": 0,
            "AVOID": 0
        }
        last_scan_utc = None

        if has_data:
            if "rdap_status" in df.columns:
                for st, count in df["rdap_status"].value_counts().items():
                    if st in status_counts:
                        status_counts[st] = int(count)
                    else:
                        status_counts["UNCERTAIN"] += int(count)

            if "tier" in df.columns:
                for t, count in df["tier"].value_counts().items():
                    if t in tier_counts:
                        tier_counts[t] = int(count)

            if "checked_utc" in df.columns and len(df["checked_utc"]) > 0:
                last_scan_utc = str(df["checked_utc"].dropna().iloc[0])

        # Counter history from scout.db
        counter_history = []
        latest_counter = None
        conn = self._get_ro_scout_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT snapshot_date, total_domains, domains_last_month, domains_last_24h, total_registrars, recorded_utc
                    FROM registry_counters ORDER BY snapshot_date ASC
                """)
                for r in cursor.fetchall():
                    counter_history.append({
                        "snapshot_date": r[0],
                        "total_domains": r[1],
                        "domains_last_month": r[2],
                        "domains_last_24h": r[3],
                        "total_registrars": r[4],
                        "recorded_utc": r[5]
                    })
                if counter_history:
                    latest_counter = counter_history[-1]
            except Exception as e:
                logger.error(f"Error reading registry counters: {e}")
            finally:
                conn.close()

        # Freshness evaluation
        cheapest_as_of = cheap_reg.as_of if cheap_reg else None
        freshness = evaluate_freshness(scan_time_iso=last_scan_utc, price_time_iso=cheapest_as_of, is_demo=self.is_demo)

        # 3 Live computed numbers for Home / Reality check
        findings_info = self.get_findings_stats()
        funnel = findings_info.get("funnel", {})
        cand_screened = funnel.get("total_candidates_generated", 100)
        reg_checked = funnel.get("registry_checked", 75)
        not_in_reg = funnel.get("not_in_registry_404", 15)
        already_taken = max(0, reg_checked - not_in_reg)

        share_registered_pct = round((already_taken / max(1, reg_checked)) * 100.0, 1)
        share_unconfirmed_pct = round((not_in_reg / max(1, reg_checked)) * 100.0, 1)

        source_file = funnel.get("source_file", "demo_data/findings_data.json" if self.is_demo else "results.csv")
        source_date = funnel.get("generation_date", "2026-10-02")

        overview_stats = {
            "candidates_screened": cand_screened,
            "checked_count": reg_checked,
            "registered_count": already_taken,
            "unconfirmed_count": not_in_reg,
            "share_registered_pct": share_registered_pct,
            "share_unconfirmed_pct": share_unconfirmed_pct,
            "source_file": source_file,
            "source_date": source_date,
        }

        return {
            "stats": overview_stats,
            "has_data": has_data,
            "total_candidates": len(df) if has_data else 0,
            "status_counts": status_counts,
            "tier_counts": tier_counts,
            "last_scan_utc": last_scan_utc,
            "budget": {
                "total_budget": 200.0,
                "reserve_amount": 20.0,
                "effective_budget": eff_budget,
                "carry_3yr_per_name": carry_3yr,
                "max_names": max_names,
                "remaining_cash": round(eff_budget - (max_names * carry_3yr), 2)
            },
            "cheapest_registrar": cheap_reg,
            "freshness": freshness,
            "counter_history": counter_history,
            "latest_counter": latest_counter
        }

    def get_candidate_detail(self, domain: str) -> Optional[Dict[str, Any]]:
        clean_domain = domain.strip().lower()
        parts = clean_domain.rsplit(".", 1)
        label = parts[0]

        df = self.get_candidates_df()
        row = None
        if not df.empty and "domain" in df.columns:
            matches = df[df["domain"] == clean_domain]
            if not matches.empty:
                row = matches.iloc[0].to_dict()

        # Fetch raw RDAP cache and twin signals from scout.db
        raw_statuses = []
        raw_json = None
        checked_utc = row.get("checked_utc") if row else None
        rdap_status = row.get("rdap_status") if row else "UNKNOWN"

        com_status = "UNKNOWN"
        com_details = ""
        ai_status = "UNKNOWN"
        ai_details = ""

        conn = self._get_ro_scout_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT rdap_status, raw_statuses_json, raw_rdap_json, checked_utc
                    FROM registry_cache WHERE domain = ?
                """, (clean_domain,))
                c_row = cursor.fetchone()
                if c_row:
                    rdap_status = c_row[0]
                    if c_row[1]:
                        raw_statuses = json.loads(c_row[1])
                    if c_row[2]:
                        raw_json = json.loads(c_row[2])
                    checked_utc = c_row[3]

                cursor.execute("""
                    SELECT com_status, com_details, ai_status, ai_details
                    FROM twin_signals WHERE label = ?
                """, (label,))
                t_row = cursor.fetchone()
                if t_row:
                    com_status = t_row[0]
                    com_details = t_row[1] or ""
                    ai_status = t_row[2]
                    ai_details = t_row[3] or ""
            except Exception as e:
                logger.error(f"Error querying scout.db detail: {e}")
            finally:
                conn.close()

        # Human rationale
        from ui.gates import validate_human_rationale
        rationales = self.get_rationales()
        rat_info = rationales.get(label)
        human_rationale = ""
        is_verified_human = False
        author = "unknown"
        rationale_status = "none"

        if rat_info:
            is_valid, msg = validate_human_rationale(rat_info)
            if isinstance(rat_info, dict):
                human_rationale = rat_info.get("rationale", "")
                author = rat_info.get("author", "unknown")
            elif isinstance(rat_info, str):
                human_rationale = rat_info
                author = "legacy"

            if is_valid:
                is_verified_human = True
                rationale_status = "verified"
            else:
                is_verified_human = False
                rationale_status = "source unknown: please rewrite"

        # Registrars comparison
        try:
            registrars = load_registrars(self.registrars_path)
        except Exception:
            registrars = {}

        registrar_options = []
        for reg_id, reg in registrars.items():
            registrar_options.append({
                "id": reg_id,
                "name": reg.name,
                "year1_usd": reg.year1_usd,
                "renewal_usd": reg.renewal_usd,
                "carry_2yr": round(reg.year1_usd + reg.renewal_usd, 2),
                "carry_3yr": reg.carry_3yr,
                "as_of": reg.as_of,
                "is_stale": reg.is_stale,
                "checkout_url": reg.get_checkout_url(clean_domain)
            })

        # Freshness of this specific candidate check
        overview = self.get_overview_stats()
        cheapest_as_of = overview["cheapest_registrar"].as_of if overview["cheapest_registrar"] else None
        cand_freshness = evaluate_freshness(
            scan_time_iso=overview["last_scan_utc"],
            check_time_iso=checked_utc,
            price_time_iso=cheapest_as_of,
            is_demo=self.is_demo
        )

        from ui.gates import check_buy_readiness, get_registrar_confirmation_remaining_minutes
        reg_conf = self.get_registrar_confirmation(clean_domain)
        reg_conf_remaining_minutes = get_registrar_confirmation_remaining_minutes(reg_conf)
        is_check_stale_60m = not cand_freshness.get("check_fresh_60m", True)
        readiness = check_buy_readiness(
            rdap_status=rdap_status,
            is_price_stale=not cand_freshness.get("price_fresh", True),
            is_scan_stale=not cand_freshness.get("scan_fresh", True),
            is_check_stale=is_check_stale_60m,
            has_trademark_flag="trademark" in str(row.get("gate_failures", "")).lower() if row else False,
            human_rationale_valid=is_verified_human,
            within_budget=True,
            registrar_confirmation=reg_conf,
            check_age_minutes=cand_freshness.get("check_age_minutes")
        )

        return {
            "domain": clean_domain,
            "label": label,
            "tier": row.get("tier", "MONITOR") if row else "MONITOR",
            "total_score": float(row.get("total_score", 0.0)) if row else 0.0,
            "rdap_status": rdap_status,
            "raw_statuses": raw_statuses,
            "raw_json": raw_json,
            "checked_utc": checked_utc or "UNKNOWN",
            "gate_failures": row.get("gate_failures", "") if row else "",
            "cheapest_registrar": row.get("cheapest_registrar", "Dynadot") if row else "Dynadot",
            "year1_usd": float(row.get("year1_usd", 12.13)) if row else 12.13,
            "carry_3yr_usd": float(row.get("carry_3yr_usd", 39.35)) if row else 39.35,
            "buy_link": row.get("buy_link", f"https://www.dynadot.com/domain/search.html?domain={clean_domain}") if row else "",
            "twin_signals": {
                "com_status": com_status,
                "com_details": com_details,
                "ai_status": ai_status,
                "ai_details": ai_details
            },
            "registrar_options": registrar_options,
            "human_rationale": human_rationale,
            "is_verified_human": is_verified_human,
            "author": author,
            "is_shortlisted": self.portfolio.is_shortlisted(clean_domain),
            "cand_freshness": cand_freshness,
            "registrar_confirmation": reg_conf,
            "reg_conf_remaining_minutes": reg_conf_remaining_minutes,
            "readiness": readiness
        }

    def get_rationales(self) -> Dict[str, Any]:
        if not self.rationales_path.exists():
            return {}
        try:
            with open(self.rationales_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_human_rationale(self, label: str, rationale: str, verified_checkbox: bool) -> Tuple[bool, str]:
        clean_label = label.strip().lower()
        from ui.gates import validate_human_rationale
        is_valid, msg = validate_human_rationale(rationale, verified_checkbox=verified_checkbox, author="human")
        if not is_valid:
            return False, msg

        now_utc = datetime.now(timezone.utc).isoformat()
        current_data = self.get_rationales()
        current_data[clean_label] = {
            "rationale": rationale.strip(),
            "word_count": len(rationale.strip().split()),
            "author": "human",
            "self_written": True,
            "timestamp": now_utc,
            "created_utc": now_utc,
            "verified_by_user": True
        }

        try:
            with open(self.rationales_path, "w", encoding="utf-8") as f:
                json.dump(current_data, f, indent=2)
            return True, "Rationale saved successfully with author='human'."
        except Exception as e:
            return False, f"Failed to save rationales.json: {e}"

    def get_limitations_markdown(self) -> str:
        if not self.limitations_path.exists():
            return "# LIMITATIONS\nLimitations document not found."
        try:
            return self.limitations_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"# LIMITATIONS\nError reading file: {e}"

    def get_drop_watch_df(self) -> pd.DataFrame:
        drop_path = self.drop_watch_path
        if not drop_path.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(drop_path, dtype=str)
        except Exception:
            return pd.DataFrame()

    def get_watchlist(self) -> List[Dict]:
        conn = self._get_ro_scout_conn()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT domain, frequency, added_utc, notes FROM watchlist ORDER BY domain ASC")
            return [{"domain": r[0], "frequency": r[1], "added_utc": r[2], "notes": r[3]} for r in cur.fetchall()]
        except Exception:
            return []
        finally:
            conn.close()

    def get_watch_log(self) -> List[Dict]:
        log_path = self.watch_log_path
        if not log_path.exists():
            return []
        try:
            df = pd.read_csv(log_path, dtype=str)
            return df.to_dict(orient="records")
        except Exception:
            return []

    # ---------------------------------------------------------
    # Gate 6 & Calibration Support
    # ---------------------------------------------------------
    def get_registrar_confirmations(self) -> Dict[str, Any]:
        if not self.confirmations_path.exists():
            return {}
        try:
            with open(self.confirmations_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_registrar_confirmation(self, domain: str) -> Optional[Dict[str, Any]]:
        confs = self.get_registrar_confirmations()
        return confs.get(domain.strip().lower())

    def save_registrar_confirmation(self, domain: str, registrar: str, result: str, checked_utc: str, notes: str = "") -> Tuple[bool, str]:
        from ui.gates import validate_registrar_confirmation
        clean_d = domain.strip().lower()
        clean_ts = "UNKNOWN" if str(checked_utc).strip().lower() == "unknown" else str(checked_utc).strip()
        entry = {
            "domain": clean_d,
            "registrar": registrar.strip(),
            "result": result.strip().lower(),
            "checked_utc": clean_ts,
            "author": "human",
            "notes": notes.strip()
        }
        is_valid, msg = validate_registrar_confirmation(entry)
        # Even if not available (e.g. taken or registry busy), save the human attempt
        confs = self.get_registrar_confirmations()
        confs[clean_d] = entry
        try:
            with open(self.confirmations_path, "w", encoding="utf-8") as f:
                json.dump(confs, f, indent=2)
            return is_valid, msg
        except Exception as e:
            return False, f"Failed to save registrar confirmation: {e}"

    def get_calibration_records(self) -> List[Dict[str, Any]]:
        if not self.calibration_path.exists():
            return []
        try:
            with open(self.calibration_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                for r in records:
                    if "registry_recheck_time" not in r:
                        r["registry_recheck_time"] = "UNKNOWN"
                    if "delta_minutes" not in r:
                        r["delta_minutes"] = self._compute_delta_minutes(r.get("registry_time_utc", ""), r.get("registrar_time_utc", ""))
                    if "delta_minutes_registry_to_registrar" not in r:
                        r["delta_minutes_registry_to_registrar"] = r["delta_minutes"]
                return records
        except Exception:
            return []

    @staticmethod
    def _compute_delta_minutes(t1_str: Any, t2_str: Any) -> Any:
        if not t1_str or not t2_str:
            return "UNKNOWN"
        s1 = str(t1_str).strip().upper()
        s2 = str(t2_str).strip().upper()
        if s1 == "UNKNOWN" or s2 == "UNKNOWN":
            return "UNKNOWN"
        try:
            dt1 = datetime.fromisoformat(str(t1_str).replace("Z", "+00:00"))
            dt2 = datetime.fromisoformat(str(t2_str).replace("Z", "+00:00"))
            return round(abs((dt2 - dt1).total_seconds()) / 60.0, 1)
        except Exception:
            return "UNKNOWN"

    def get_calibration_stats(self) -> Dict[str, Any]:
        records = self.get_calibration_records()
        total = len(records)
        agrees = sum(1 for r in records if r.get("agrees") is True)
        disagrees = total - agrees
        rate = round((agrees / total) * 100.0, 1) if total > 0 else 0.0
        return {
            "total_count": total,
            "agrees_count": agrees,
            "disagrees_count": disagrees,
            "agreement_rate": rate,
            "is_fewer_than_10": total < 10,
            "records": records
        }

    def add_calibration_record(self, domain: str, registry_status: str, registry_time_utc: str,
                               registrar_name: str, registrar_result: str, registrar_time_utc: str,
                               notes: str = "", registry_recheck_time: Optional[str] = None) -> Dict[str, Any]:
        records = self.get_calibration_records()
        reg_clean = str(registry_status).lower()
        res_clean = str(registrar_result).lower()

        # Agreement logic:
        # Registry says 404 / available candidate -> Registrar must report available to agree
        is_reg_avail = ("404" in reg_clean or "available" in reg_clean or "not in registry" in reg_clean)
        is_res_avail = (res_clean == "available")
        if is_reg_avail:
            agrees = is_res_avail
        else:
            agrees = (res_clean in ["taken", "already taken"])

        clean_reg_recheck = str(registry_recheck_time).strip() if registry_recheck_time and str(registry_recheck_time).strip() else "UNKNOWN"
        clean_registrar_time = "UNKNOWN" if str(registrar_time_utc).strip().lower() == "unknown" else str(registrar_time_utc).strip()
        delta = self._compute_delta_minutes(registry_time_utc, clean_registrar_time)

        new_record = {
            "id": len(records) + 1,
            "domain": domain.strip().lower(),
            "registry_status": registry_status.strip(),
            "registry_time_utc": registry_time_utc.strip(),
            "registry_recheck_time": clean_reg_recheck,
            "registrar_name": registrar_name.strip(),
            "registrar_result": registrar_result.strip().lower(),
            "registrar_time_utc": clean_registrar_time,
            "delta_minutes": delta,
            "delta_minutes_registry_to_registrar": delta,
            "agrees": agrees,
            "author": "human",
            "notes": notes.strip()
        }
        records.append(new_record)
        with open(self.calibration_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        return new_record

    def get_findings_stats(self) -> Dict[str, Any]:
        """Computes findings summary strictly from data files (demo fixtures or local scan files).
        Every stat returned has an explicit source_file and generation_date.
        """
        findings_json_path = self.findings_path
        funnel_data: Dict[str, Any] = {
            "total_candidates_generated": 0,
            "prefiltered_survivors": 0,
            "registry_checked": 0,
            "not_in_registry_404": 0,
            "strict_survivors": 0,
            "stage_descriptions": [],
            "source_file": str(findings_json_path.as_posix()),
            "generation_date": "UNKNOWN"
        }
        saturation_data: Dict[str, Any] = {
            "patterns": [],
            "source_file": str(findings_json_path.as_posix()),
            "generation_date": "UNKNOWN"
        }

        if findings_json_path.exists():
            try:
                with open(findings_json_path, "r", encoding="utf-8") as f:
                    raw_findings = json.load(f)
                    f_meta = raw_findings.get("metadata", {})
                    gen_date = f_meta.get("generation_date_utc", "UNKNOWN")
                    s_file = f_meta.get("source_file", str(findings_json_path.as_posix()))

                    if "funnel" in raw_findings:
                        funnel_data = dict(raw_findings["funnel"])
                        funnel_data["source_file"] = s_file
                        funnel_data["generation_date"] = gen_date

                    if "saturation_by_pattern" in raw_findings:
                        saturation_data["patterns"] = raw_findings["saturation_by_pattern"]
                        saturation_data["source_file"] = s_file
                        saturation_data["generation_date"] = gen_date
            except Exception as e:
                logger.error(f"Error reading findings json: {e}")

        # Registry counter time series
        counter_series = []
        counter_source = str(self.db_path.as_posix()) + " (registry_counters)"
        counter_gen_date = "UNKNOWN"
        conn = self._get_ro_scout_conn()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT snapshot_date, total_domains, domains_last_month, domains_last_24h, recorded_utc
                    FROM registry_counters ORDER BY snapshot_date ASC
                """)
                for r in cur.fetchall():
                    counter_series.append({
                        "snapshot_date": r[0],
                        "total_domains": r[1],
                        "domains_last_month": r[2],
                        "domains_last_24h": r[3],
                        "recorded_utc": r[4]
                    })
                if counter_series:
                    counter_gen_date = counter_series[-1]["recorded_utc"]
            except Exception as e:
                logger.error(f"Error fetching counter series: {e}")
            finally:
                conn.close()

        counter_data = {
            "series": counter_series,
            "source_file": counter_source,
            "generation_date": counter_gen_date,
            "caption": "Shows whether the rush continues, not a prediction."
        }

        # Calibration summary
        cal_stats = self.get_calibration_stats()
        cal_source = str(self.calibration_path.as_posix())
        cal_gen_date = "UNKNOWN"
        if cal_stats.get("records"):
            dates = [r.get("registry_time_utc") for r in cal_stats["records"] if r.get("registry_time_utc") and r.get("registry_time_utc") != "UNKNOWN"]
            if dates:
                cal_gen_date = max(dates)

        calibration_summary = {
            "total_count": cal_stats.get("total_count", 0),
            "agrees_count": cal_stats.get("agrees_count", 0),
            "disagrees_count": cal_stats.get("disagrees_count", 0),
            "agreement_rate": cal_stats.get("agreement_rate", 0.0),
            "is_fewer_than_10": cal_stats.get("is_fewer_than_10", True),
            "source_file": cal_source,
            "generation_date": cal_gen_date
        }

        return {
            "is_demo": self.is_demo,
            "demo_badge_text": "Illustrative demo data" if self.is_demo else "Local scan data",
            "funnel": funnel_data,
            "saturation": saturation_data,
            "counter": counter_data,
            "calibration": calibration_summary
        }



