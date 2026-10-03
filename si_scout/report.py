"""
Report Generator for SI Scout.
Emits results.csv and report.md with 3 tiers (BUY_CANDIDATE, MONITOR, AVOID),
source timestamps, budget carry trade-offs, and an illustrative EV scenario matrix (not a forecast).
"""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from si_scout.score import CandidateEvaluation, CandidateTier

class ReportGenerator:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(".")

    def generate_ev_table_markdown(self, carry_3yr: float = 39.35) -> str:
        """
        Generates an illustrative EV calculation table across conservative sell-through rates.
        Explicitly labelled as illustrative scenario model, NOT a forecast.
        """
        lines = [
            "### Illustrative Expected-Value Scenario Matrix",
            "> [!IMPORTANT]",
            "> **Disclaimer**: This table is purely illustrative scenario modeling, **not a forecast, promise, or expectation of profit**.",
            "> Domain investing carries high liquidity risk and expected value for small portfolios is typically negative.",
            "",
            "| Scenario | Annual Sell-Through | 3-Year Cumulative Sell-Through | Resale Price | Expected Gross Revenue (per domain) | 3-Yr Holding Cost | Expected Net (per domain) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        scenarios = [
            ("Conservative Baseline", 0.01, 500.0),
            ("Moderate Target", 0.02, 1000.0),
            ("Optimistic Bull", 0.03, 2000.0)
        ]

        for name, annual_rate, sale_price in scenarios:
            cum_rate = 1.0 - ((1.0 - annual_rate) ** 3)
            exp_rev = cum_rate * sale_price
            exp_net = exp_rev - carry_3yr
            lines.append(
                f"| {name} | {annual_rate*100:.1f}% | {cum_rate*100:.1f}% | ${sale_price:,.2f} | ${exp_rev:.2f} | ${carry_3yr:.2f} | **${exp_net:+.2f}** |"
            )

        return "\n".join(lines)

    def generate_reports(self,
                         evaluations: List[CandidateEvaluation],
                         budget_info: Dict[str, Any],
                         pricing_map: Dict[str, Dict]) -> Tuple[Path, Path]:
        timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 1. Generate results.csv
        csv_path = self.output_dir / "results.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "domain", "label", "tier", "total_score", "rdap_status",
                "cheapest_registrar", "year1_usd", "carry_3yr_usd",
                "buy_link", "human_rationale", "gate_failures", "checked_utc"
            ])
            for ev in evaluations:
                pr = pricing_map.get(ev.domain, {})
                cheap = pr.get("cheapest_registrar") or {}
                writer.writerow([
                    ev.domain,
                    ev.label,
                    ev.tier.value,
                    ev.total_score,
                    ev.rdap_status.value,
                    cheap.get("name", "UNKNOWN"),
                    cheap.get("year1_usd", "UNKNOWN"),
                    cheap.get("carry_3yr", "UNKNOWN"),
                    pr.get("buy_link", "N/A"),
                    ev.human_rationale,
                    "; ".join(ev.gate_failures),
                    timestamp_utc
                ])

        # 2. Generate report.md
        md_path = self.output_dir / "report.md"
        carry_3yr = budget_info.get("carry_3yr_per_name", 39.35)
        max_names = budget_info.get("max_names", 4)
        eff_budget = budget_info.get("effective_budget", 180.0)

        buy_candidates = [e for e in evaluations if e.tier == CandidateTier.BUY_CANDIDATE]
        monitor_candidates = [e for e in evaluations if e.tier == CandidateTier.MONITOR]
        avoid_candidates = [e for e in evaluations if e.tier == CandidateTier.AVOID]

        lines = [
            "# SI Scout: Research & Recommendation Report",
            f"**Generated**: `{timestamp_utc}` | **Evaluation Horizon**: 3-Year Carry | **Budget Cap**: $200.00 USD",
            "",
            "## 1. Budget Model & Capital Allocation",
            f"- **Total Budget**: ${budget_info.get('total_budget', 200.0):.2f} USD",
            f"- **Emergency/Tax Reserve (10%)**: ${budget_info.get('reserve_amount', 20.0):.2f} USD",
            f"- **Net Investable Capital**: ${eff_budget:.2f} USD",
            f"- **Estimated 3-Year Carry Cost**: ${carry_3yr:.2f} per domain (`year1 + 2 * renewal`)",
            f"- **Maximum Portfolio Size**: **{max_names} names** (locks capital into ~{max_names} names; protects against renewal repricing)",
            "",
            "## 2. Epistemic Baseline & Ground Truths",
            "> [!NOTE]",
            "> **The Truth About This Market**: High scores reflect compliance with strict screening heuristics, **and do not indicate future market value, resale liquidity, or capital appreciation**.",
            "> Domain sales in `.si` for end users are historically scarce (only 2 verified in public early-2026 sales).",
            "> Treat any purchase as an asymmetric lottery ticket with an all-in downside capped at $200.",
            "",
            "---",
            "",
            f"## 3. Tier 1: BUY_CANDIDATE ({len(buy_candidates)} names)",
            "All non-negotiable gates passed: Verified available via live RDAP, fresh price, no trademark hits, and validated human end-user rationale.",
            ""
        ]

        if not buy_candidates:
            lines.append("*No candidates currently meet all strict BUY_CANDIDATE gates (requires human end-user sentence and active RDAP availability).*")
        else:
            lines.append("| Domain | Score | 1-Yr Cost | 3-Yr Carry | Cheapest Registrar | Buy Link (Verify at checkout) | Human Rationale |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for ev in buy_candidates:
                pr = pricing_map.get(ev.domain, {})
                cheap = pr.get("cheapest_registrar") or {}
                link = pr.get("buy_link", "#")
                lines.append(
                    f"| **{ev.domain}** | {ev.total_score} | ${cheap.get('year1_usd', 0):.2f} | ${cheap.get('carry_3yr', 0):.2f} | {cheap.get('name', 'N/A')} | [Checkout Link]({link}) | {ev.human_rationale} |"
                )

        lines.extend([
            "",
            "---",
            "",
            f"## 4. Tier 2: MONITOR ({len(monitor_candidates)} names)",
            "Promising candidates that are either registered, pending delete/quarantine, or awaiting human rationale formulation.",
            "",
            "| Domain | Score | RDAP Status | Missing Gate / Reason | Notes |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ])

        for ev in monitor_candidates[:25]:
            reasons = "; ".join(ev.gate_failures) if ev.gate_failures else "Awaiting manual gate review"
            lines.append(f"| `{ev.domain}` | {ev.total_score} | {ev.rdap_status.value} | {reasons} | {'; '.join(ev.breakdown.rationale_notes[:2])} |")

        lines.extend([
            "",
            "---",
            "",
            f"## 5. Tier 3: AVOID ({len(avoid_candidates)} names)",
            "Names blocked due to trademark conflict risk, official registry reservation, or poor phonetic structure.",
            "",
            "| Domain | RDAP Status | Block Reason / Gate Failures |",
            "| :--- | :--- | :--- |"
        ])

        for ev in avoid_candidates[:15]:
            reasons = "; ".join(ev.gate_failures) if ev.gate_failures else "Blocked by heuristics"
            lines.append(f"| `{ev.domain}` | {ev.rdap_status.value} | {reasons} |")

        lines.extend([
            "",
            "---",
            "",
            "## 6. Financial Scenario Analysis",
            self.generate_ev_table_markdown(carry_3yr=carry_3yr),
            "",
            "---",
            "",
            "## 7. Compliance & Regulatory Mandatory Notice",
            "- **Real Identity Requirement (NIS2 Directive)**: `.si` domain holders are legally required to provide accurate, verified registrant contact details.",
            "- **Do NOT use proxies, anonymizers, or fake names**. Inaccurate contact information will result in registry suspension across all linked domains.",
            "- **Dispute Policy**: The ARNES dispute resolution process (ARDS) can revoke domains infringing on recognized trademarks."
        ])

        md_path.write_text("\n".join(lines), encoding="utf-8")
        return md_path, csv_path
