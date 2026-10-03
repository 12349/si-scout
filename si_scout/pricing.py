"""
Pricing Engine and Marketplace Link Generator for SI Scout.
Computes effective 1-year and 3-year costs, identifies cheapest non-stale registrar,
and generates links with mandatory confirmation warnings.
"""

from typing import Dict, List, Optional
from si_scout.config import RegistrarInfo, load_registrars, get_cheapest_registrar

AFTERMARKET_TEMPLATES = {
    "sedo": "https://sedo.com/search/?keyword={domain}",
    "afternic": "https://www.afternic.com/search?k={domain}",
    "dan": "https://dan.com/buy-domain/{domain}"
}

class PricingEngine:
    def __init__(self, registrars: Optional[Dict[str, RegistrarInfo]] = None):
        self.registrars = registrars or load_registrars()

    def get_pricing_summary(self, domain: str) -> Dict:
        """
        Computes pricing options for an available candidate domain.
        Returns cheapest non-stale registrar option, direct buy link, and disclaimers.
        """
        cheapest = get_cheapest_registrar(self.registrars, allow_stale=False)

        all_options = []
        for reg_id, reg in self.registrars.items():
            all_options.append({
                "registrar_id": reg_id,
                "name": reg.name,
                "year1_usd": reg.year1_usd,
                "renewal_usd": reg.renewal_usd,
                "carry_3yr": reg.carry_3yr,
                "is_stale": reg.is_stale,
                "as_of": reg.as_of,
                "checkout_url": reg.get_checkout_url(domain)
            })

        cheapest_info = None
        buy_link = ""
        if cheapest:
            cheapest_info = {
                "registrar_id": cheapest.id,
                "name": cheapest.name,
                "year1_usd": cheapest.year1_usd,
                "renewal_usd": cheapest.renewal_usd,
                "carry_3yr": cheapest.carry_3yr,
                "is_stale": cheapest.is_stale,
                "as_of": cheapest.as_of
            }
            buy_link = cheapest.get_checkout_url(domain)

        return {
            "domain": domain,
            "cheapest_registrar": cheapest_info,
            "buy_link": buy_link,
            "all_options": all_options,
            "disclaimer": "Confirm premium/reserved status and final renewal price at registrar checkout."
        }

    def get_aftermarket_links(self, domain: str) -> Dict[str, str]:
        """Generates marketplace search links for registered domains."""
        clean = domain.strip().lower()
        return {
            platform: tmpl.format(domain=clean)
            for platform, tmpl in AFTERMARKET_TEMPLATES.items()
        }
