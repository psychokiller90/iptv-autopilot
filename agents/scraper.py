import os
import re
import json
import logging
import urllib.request
import urllib.parse
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] %(message)s")
logger = logging.getLogger("ScraperAgent")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class ScraperAgent:
    """Agent 1 : Moissonneur de flux IPTV sur GitHub et dépôts de référence."""

    def __init__(self, config_path: str = "config/sources.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    def run(self) -> List[Dict[str, Any]]:
        logger.info("🚀 Démarrage de l'Agent 1 (Scraper)...")
        channels = []

        # 1. Moissonnage des sources de référence (Seeds)
        for seed in self.config.get("seed_sources", []):
            try:
                logger.info(f"📥 Récupération de la source : {seed['name']} ({seed['url']})")
                raw_content = self._fetch_url(seed["url"])
                if not raw_content:
                    continue

                if seed.get("type") == "dcmp_markdown":
                    parsed = self._parse_dcmp_markdown(raw_content, seed["name"])
                else:
                    parsed = self._parse_m3u(raw_content, default_country=seed.get("country", "ALL"), source_name=seed["name"])

                logger.info(f"  -> {len(parsed)} chaînes extraites de {seed['name']}")
                channels.extend(parsed)
            except Exception as e:
                logger.warning(f"⚠️ Échec lors de la lecture de {seed['name']} : {e}")

        # 2. Découverte via GitHub Search API (si token disponible)
        if self.github_token:
            logger.info("🔍 Recherche dynamique de nouveaux dépôts IPTV sur GitHub...")
            discovered_channels = self._search_github_repositories()
            logger.info(f"  -> {len(discovered_channels)} chaînes découvertes via GitHub Search")
            channels.extend(discovered_channels)
        else:
            logger.info("ℹ️ Pas de GITHUB_TOKEN fourni : recherche GitHub Search ignorée (utilisation des seeds).")

        # 3. Déduplication et nettoyage
        unique_channels = self._deduplicate_and_clean(channels)
        logger.info(f"✅ Moissonnage terminé : {len(unique_channels)} flux uniques prêts pour l'audit.")
        return unique_channels

    def _fetch_url(self, url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.debug(f"Erreur HTTP sur {url}: {e}")
            return ""

    def _parse_m3u(self, content: str, default_country: str = "ALL", source_name: str = "seed") -> List[Dict[str, Any]]:
        channels = []
        lines = content.splitlines()
        current_meta = None
        current_ua = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("#EXTINF:"):
                current_meta = line
                current_ua = None
            elif line.startswith("#EXTVLCOPT:http-user-agent=") or line.startswith("#EXTVLCOPT:user-agent="):
                current_ua = line.split("=", 1)[1].strip()
            elif line.startswith("http://") or line.startswith("https://"):
                if current_meta:
                    chan = self._extract_channel_info(current_meta, line, current_ua, default_country, source_name)
                    if chan:
                        channels.append(chan)
                current_meta = None
                current_ua = None

        return channels

    def _extract_channel_info(self, extinf: str, url: str, ua: str, default_country: str, source_name: str) -> Dict[str, Any]:
        # Extraction du nom de chaîne après la virgule
        name = extinf.split(",")[-1].strip()
        if not name:
            name = "Chaîne Inconnue"

        # Regex pour les attributs EXTINF
        tvg_id = self._regex_attr(r'tvg-id="([^"]*)"', extinf)
        tvg_name = self._regex_attr(r'tvg-name="([^"]*)"', extinf) or name
        tvg_logo = self._regex_attr(r'tvg-logo="([^"]*)"', extinf)
        group = self._regex_attr(r'group-title="([^"]*)"', extinf) or "General"
        country = self._regex_attr(r'tvg-country="([^"]*)"', extinf) or default_country
        extinf_ua = self._regex_attr(r'http-user-agent="([^"]*)"', extinf) or ua

        # Détection du pays si non spécifié
        if country == "ALL":
            country = self._detect_country(name, tvg_id, group)

        # Normalisation de la catégorie
        group = self._normalize_category(group, name)

        return {
            "name": name,
            "url": url,
            "tvg_id": tvg_id,
            "tvg_name": tvg_name,
            "logo": tvg_logo,
            "group": group,
            "country": country.upper(),
            "user_agent": extinf_ua or USER_AGENT,
            "source": source_name
        }

    def _regex_attr(self, pattern: str, text: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _parse_dcmp_markdown(self, content: str, source_name: str) -> List[Dict[str, Any]]:
        channels = []
        pattern = r'\"description\"\s*:\s*\"([^\"]*)\".*?\"sources\"\s*:\s*\[\"([^\"]+)\"\].*?\"thumb\"\s*:\s*\"([^\"]*)\".*?\"title\"\s*:\s*(?:\"description\":)?\"([^\"]+)\"'
        items = re.findall(pattern, content, re.DOTALL)
        for desc, src, thumb, title in items:
            url = src.strip()
            name = title.strip()
            if url and name and (url.startswith("http://") or url.startswith("https://")):
                channels.append({
                    "name": name,
                    "url": url,
                    "tvg_id": "",
                    "tvg_name": name,
                    "logo": thumb.strip(),
                    "group": self._normalize_category(desc, name),
                    "country": "FR",
                    "user_agent": USER_AGENT,
                    "source": source_name
                })
        return channels


    def _search_github_repositories(self) -> List[Dict[str, Any]]:
        channels = []
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "IPTV-Autopilot-Scraper"
        }

        for query in self.config.get("github_search_queries", []):
            try:
                encoded_query = urllib.parse.quote(query)
                search_url = f"https://api.github.com/search/code?q={encoded_query}&per_page=5"
                req = urllib.request.Request(search_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    for item in data.get("items", []):
                        html_url = item.get("html_url", "")
                        if "github.com" in html_url:
                            raw_url = html_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                            raw_content = self._fetch_url(raw_url)
                            if raw_content and "#EXTINF" in raw_content:
                                found = self._parse_m3u(raw_content, default_country="ALL", source_name=item.get("repository", {}).get("full_name", "github_search"))
                                channels.extend(found[:80]) # Limite par fichier découvert
            except Exception as e:
                logger.debug(f"Erreur recherche GitHub pour '{query}': {e}")
        return channels

    def _detect_country(self, name: str, tvg_id: str, group: str) -> str:
        text = f"{name} {tvg_id} {group}".lower()
        if any(w in text for w in [".fr", "france", "francais", "français", "tnt", "tf1", "m6", "canal+", "arte"]):
            return "FR"
        if any(w in text for w in [".us", "usa", "american", "nbc", "cbs", "abc", "fox"]):
            return "US"
        if any(w in text for w in [".uk", "bbc", "itv", "sky uk", "united kingdom"]):
            return "UK"
        if any(w in text for w in [".be", "belgique", "rtbf", "vrt"]):
            return "BE"
        if any(w in text for w in [".ch", "suisse", "rts", "srf"]):
            return "CH"
        if any(w in text for w in [".ca", "canada", "tva", "cbc"]):
            return "CA"
        return "GLOBAL"

    def _normalize_category(self, group: str, name: str) -> str:
        combined = f"{group} {name}".lower()
        mapping = self.config.get("categories_mapping", {})
        for cat, keywords in mapping.items():
            if any(k in combined for k in keywords):
                return cat
        return "General"

    def _deduplicate_and_clean(self, channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_urls = set()
        clean_list = []
        blacklist = [b.lower() for b in self.config.get("blacklist_keywords", [])]

        for ch in channels:
            url = ch.get("url", "").strip()
            name = ch.get("name", "").strip()
            if not url or url in seen_urls:
                continue

            # Vérification blacklist
            name_lower = name.lower()
            if any(b in name_lower for b in blacklist):
                continue

            seen_urls.add(url)
            clean_list.append(ch)

        return clean_list

if __name__ == "__main__":
    scraper = ScraperAgent()
    results = scraper.run()
    print(f"Total chaînes scrapées : {len(results)}")
