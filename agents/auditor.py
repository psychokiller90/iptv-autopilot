import asyncio
import aiohttp
import time
import logging
from urllib.parse import urljoin
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("AuditorAgent")

class AuditorAgent:
    """Agent 2 : Auditeur haute cadence de viabilité des flux HLS et segments vidéo."""

    def __init__(self, concurrency: int = 40, timeout: float = 4.5):
        self.concurrency = concurrency
        self.timeout = aiohttp.ClientTimeout(total=timeout, connect=2.5)

    def run(self, channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info(f"🔬 Démarrage de l'Agent 2 (Auditeur) sur {len(channels)} flux...")
        start_time = time.time()

        # Exécution de la boucle asynchrone
        valid_channels = asyncio.run(self._audit_all(channels))

        elapsed = round(time.time() - start_time, 2)
        rate = round(len(valid_channels) / len(channels) * 100, 1) if channels else 0
        logger.info(f"✅ Audit terminé en {elapsed}s : {len(valid_channels)}/{len(channels)} flux opérationnels ({rate}%).")
        return valid_channels

    async def _audit_all(self, channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        connector = aiohttp.TCPConnector(limit=self.concurrency, ssl=False, force_close=True)
        semaphore = asyncio.Semaphore(self.concurrency)
        valid_channels = []

        async with aiohttp.ClientSession(connector=connector, timeout=self.timeout) as session:
            tasks = [self._test_channel(session, semaphore, ch) for ch in channels]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, tuple) and res[0] is True:
                    valid_channels.append(res[1])

        return valid_channels

    async def _test_channel(self, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, channel: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        url = channel["url"]
        user_agent = channel.get("user_agent") or "Mozilla/5.0"
        headers = {
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Connection": "close"
        }

        async with semaphore:
            t0 = time.time()
            try:
                # Étape 1 : Téléchargement du fichier manifest m3u8
                async with session.get(url, headers=headers, allow_redirects=True) as resp:
                    if resp.status >= 400:
                        return False, channel

                    # Vérification préliminaire du contenu (évite de lire des Go)
                    body_bytes = await resp.content.read(16384)
                    body_text = body_bytes.decode("utf-8", errors="ignore")

                    # Rejet immédiat des faux positifs HTML (pages d'erreur 200 OK)
                    if "<!doctype" in body_text.lower() or "<html" in body_text.lower():
                        return False, channel

                    # Vérification qu'il s'agit bien d'une playlist HLS
                    if not ("#EXTM3U" in body_text or "#EXT-X-" in body_text):
                        return False, channel

                    # Étape 2 : Extraction et test du premier segment vidéo
                    segment_url = self._extract_first_segment(url, body_text)
                    if not segment_url:
                        # Si pas de segment direct (ex: master playlist imbriquée), on teste le sous-manifest
                        sub_manifest = self._extract_first_submanifest(url, body_text)
                        if sub_manifest:
                            async with session.get(sub_manifest, headers=headers, allow_redirects=True) as sub_resp:
                                if sub_resp.status < 400:
                                    sub_body = (await sub_resp.content.read(16384)).decode("utf-8", errors="ignore")
                                    segment_url = self._extract_first_segment(sub_manifest, sub_body)

                    # Si un segment est trouvé, on teste le téléchargement partiel (Range: 0-1024)
                    if segment_url:
                        seg_headers = headers.copy()
                        seg_headers["Range"] = "bytes=0-1024"
                        async with session.get(segment_url, headers=seg_headers, allow_redirects=True) as seg_resp:
                            if seg_resp.status not in (200, 206):
                                return False, channel

                    latency = int((time.time() - t0) * 1000)
                    channel_copy = channel.copy()
                    channel_copy["latency_ms"] = latency
                    channel_copy["status"] = "ONLINE"
                    return True, channel_copy

            except Exception:
                return False, channel

    def _extract_first_segment(self, base_url: str, m3u8_text: str) -> str:
        for line in m3u8_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Ignorer les sous-playlists master
            if line.endswith(".m3u8") or ".m3u8?" in line:
                continue
            # Premier segment valide trouvé
            return urljoin(base_url, line)
        return ""

    def _extract_first_submanifest(self, base_url: str, m3u8_text: str) -> str:
        for line in m3u8_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith(".m3u8") or ".m3u8?" in line:
                return urljoin(base_url, line)
        return ""

if __name__ == "__main__":
    auditor = AuditorAgent(concurrency=20)
    test_channels = [
        {"name": "Arte", "url": "https://artesimulcast.akamaized.net/hls/live/2031003/artelive_fr/index.m3u8"},
        {"name": "Dead Stream", "url": "http://99.27.51.147/CineClassic/index.m3u8"}
    ]
    verified = auditor.run(test_channels)
    print("Vérifiées :", [c["name"] for c in verified])
