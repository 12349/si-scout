"""
Portfolio Database Storage for SI Scout UI.
Maintains post-purchase assets, inquiry logs, outreach tracker, shortlist, and kill criteria.
Stored separately in portfolio.db, completely distinct from scanner cache.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class PortfolioStore:
    def __init__(self, db_path: Optional[Path] = None):
        target = Path(db_path) if db_path else Path("portfolio.db")
        if str(target) != ":memory:":
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                probe = target.parent / f".probe_{os.getpid()}"
                probe.write_text("1", encoding="utf-8")
                probe.unlink()
            except (OSError, PermissionError):
                # Fallback to writable temporary location
                target = Path(tempfile.gettempdir()) / "si_scout_portfolio.db"
        self.db_path = target
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = None
        try:
            if str(self.db_path) != ":memory:":
                try:
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)
                except OSError:
                    pass
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.OperationalError:
            try:
                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                yield conn
            except Exception:
                raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio_items (
                        domain TEXT PRIMARY KEY,
                        purchase_date TEXT NOT NULL,
                        price_paid REAL NOT NULL,
                        registrar TEXT NOT NULL,
                        renewal_date TEXT NOT NULL,
                        refund_deadline TEXT NOT NULL,
                        asking_price REAL,
                        status TEXT DEFAULT 'HOLDING',
                        notes TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS inquiries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        domain TEXT NOT NULL,
                        inquiry_date TEXT NOT NULL,
                        inquirer TEXT NOT NULL,
                        offer_usd REAL,
                        notes TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS outreach_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company TEXT NOT NULL,
                        contact_person TEXT,
                        date_contacted TEXT NOT NULL,
                        reply_status TEXT DEFAULT 'PENDING',
                        notes TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shortlist (
                        domain TEXT PRIMARY KEY,
                        added_utc TEXT NOT NULL,
                        notes TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS kill_criteria (
                        id INTEGER PRIMARY KEY,
                        contract_text TEXT NOT NULL,
                        updated_utc TEXT NOT NULL
                    )
                """)
                # Initialize default kill criteria if missing
                cursor.execute("SELECT COUNT(*) FROM kill_criteria")
                if cursor.fetchone()[0] == 0:
                    default_text = "If by the first renewal cycle (Sept–Oct 2027) I have received zero inbound inquiries and observed no comparable end-user sales, I will not renew any names and cap loss at the initial purchase price."
                    cursor.execute("INSERT INTO kill_criteria (id, contract_text, updated_utc) VALUES (1, ?, ?)",
                                   (default_text, datetime.now(timezone.utc).isoformat()))
                conn.commit()
        except Exception as e:
            logger.warning(f"PortfolioStore _init_db non-fatal: {e}")

    # Shortlist operations
    def get_shortlist(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT domain, added_utc, notes FROM shortlist ORDER BY added_utc DESC")
            return [{"domain": r[0], "added_utc": r[1], "notes": r[2]} for r in cursor.fetchall()]

    def toggle_shortlist(self, domain: str, notes: str = "") -> bool:
        clean = domain.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT domain FROM shortlist WHERE domain = ?", (clean,))
            if cursor.fetchone():
                cursor.execute("DELETE FROM shortlist WHERE domain = ?", (clean,))
                conn.commit()
                return False
            else:
                now_utc = datetime.now(timezone.utc).isoformat()
                cursor.execute("INSERT INTO shortlist (domain, added_utc, notes) VALUES (?, ?, ?)", (clean, now_utc, notes))
                conn.commit()
                return True

    def is_shortlisted(self, domain: str) -> bool:
        clean = domain.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT domain FROM shortlist WHERE domain = ?", (clean,))
            return cursor.fetchone() is not None

    # Portfolio items operations
    def get_portfolio_items(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT domain, purchase_date, price_paid, registrar, renewal_date, refund_deadline, asking_price, status, notes
                FROM portfolio_items ORDER BY purchase_date DESC
            """)
            rows = cursor.fetchall()
            items = []
            for r in rows:
                items.append({
                    "domain": r[0],
                    "purchase_date": r[1],
                    "price_paid": r[2],
                    "registrar": r[3],
                    "renewal_date": r[4],
                    "refund_deadline": r[5],
                    "asking_price": r[6],
                    "status": r[7],
                    "notes": r[8]
                })
            return items

    def add_portfolio_item(self, domain: str, purchase_date: str, price_paid: float,
                           registrar: str, asking_price: Optional[float] = None, notes: str = ""):
        clean = domain.strip().lower()
        p_dt = datetime.fromisoformat(purchase_date)
        refund_dt = p_dt + timedelta(days=16)
        renewal_dt = p_dt + timedelta(days=365)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO portfolio_items
                (domain, purchase_date, price_paid, registrar, renewal_date, refund_deadline, asking_price, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'HOLDING', ?)
            """, (
                clean,
                p_dt.strftime("%Y-%m-%d"),
                price_paid,
                registrar,
                renewal_dt.strftime("%Y-%m-%d"),
                refund_dt.strftime("%Y-%m-%d"),
                asking_price,
                notes
            ))
            conn.commit()

    # Outreach log operations
    def get_outreach_log(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, company, contact_person, date_contacted, reply_status, notes FROM outreach_log ORDER BY date_contacted DESC")
            return [{
                "id": r[0], "company": r[1], "contact_person": r[2],
                "date_contacted": r[3], "reply_status": r[4], "notes": r[5]
            } for r in cursor.fetchall()]

    def add_outreach(self, company: str, contact_person: str, date_contacted: str, reply_status: str, notes: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO outreach_log (company, contact_person, date_contacted, reply_status, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (company.strip(), contact_person.strip(), date_contacted.strip(), reply_status.strip(), notes.strip()))
            conn.commit()

    # Kill criteria operations
    def get_kill_criteria(self) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT contract_text FROM kill_criteria WHERE id = 1")
            row = cursor.fetchone()
            return row[0] if row else ""

    def update_kill_criteria(self, text: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_utc = datetime.now(timezone.utc).isoformat()
            cursor.execute("INSERT OR REPLACE INTO kill_criteria (id, contract_text, updated_utc) VALUES (1, ?, ?)",
                           (text.strip(), now_utc))
            conn.commit()
