import pytest
import sqlite3
import pandas as pd
from pathlib import Path
from ui.data import UIDataManager

def test_data_manager_missing_files(tmp_path):
    mgr = UIDataManager(
        csv_path=tmp_path / "nonexistent.csv",
        db_path=tmp_path / "nonexistent.db",
        portfolio_db_path=tmp_path / "portfolio.db",
        rationales_path=tmp_path / "rationales.json"
    )
    # Must handle missing files gracefully without throwing unhandled exceptions
    df = mgr.get_candidates_df()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0

    overview = mgr.get_overview_stats()
    assert overview["has_data"] is False
    assert overview["total_candidates"] == 0

def test_data_manager_empty_or_malformed_csv(tmp_path):
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("not,a,proper,csv\n1,2", encoding="utf-8")
    
    mgr = UIDataManager(
        csv_path=csv_file,
        db_path=tmp_path / "empty.db",
        portfolio_db_path=tmp_path / "portfolio.db",
        rationales_path=tmp_path / "rationales.json"
    )
    df = mgr.get_candidates_df()
    assert isinstance(df, pd.DataFrame)

def test_data_manager_normal_read(tmp_path):
    csv_file = tmp_path / "results.csv"
    csv_content = """domain,label,tier,total_score,rdap_status,cheapest_registrar,year1_usd,carry_3yr_usd,buy_link,human_rationale,gate_failures,checked_utc
synthgrid.si,synthgrid,BUY_CANDIDATE,64.5,AVAILABLE_CANDIDATE,Dynadot,12.13,39.35,https://example.com,A company rationale here,,2026-09-30 19:20:18 UTC
neurocore.si,neurocore,AVOID,61.5,REGISTERED,Dynadot,12.13,39.35,https://example.com,Rationale,Domain taken,2026-09-30 19:20:18 UTC
"""
    csv_file.write_text(csv_content, encoding="utf-8")

    db_file = tmp_path / "scout.db"
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE registry_counters (
                snapshot_date TEXT PRIMARY KEY,
                total_domains INTEGER,
                domains_last_month INTEGER,
                domains_last_24h INTEGER,
                total_registrars INTEGER,
                recorded_utc TEXT
            )
        """)
        conn.execute("INSERT INTO registry_counters VALUES ('2026-09-30', 233560, 3515, 10859, 92, '2026-09-30T19:00:00Z')")
        conn.commit()

    mgr = UIDataManager(
        csv_path=csv_file,
        db_path=db_file,
        portfolio_db_path=tmp_path / "portfolio.db",
        rationales_path=tmp_path / "rationales.json"
    )
    df = mgr.get_candidates_df()
    assert len(df) == 2
    assert "synthgrid.si" in df["domain"].values

    stats = mgr.get_overview_stats()
    assert stats["has_data"] is True
    assert stats["status_counts"]["AVAILABLE_CANDIDATE"] == 1
    assert stats["status_counts"]["REGISTERED"] == 1
    assert stats["latest_counter"]["total_domains"] == 233560
