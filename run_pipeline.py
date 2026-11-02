import os
import sys
import time
import logging
from agents.scraper import ScraperAgent
from agents.auditor import AuditorAgent
from agents.publisher import PublisherAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("PipelineCoordinator")

def main():
    start_time = time.time()
    logger.info("=" * 65)
    logger.info("🚀 DÉMARRAGE DU PIPELINE MULTI-AGENTS IPTV AUTOPILOT")
    logger.info("=" * 65)

    # 1. Agent 1 : Scraper
    scraper = ScraperAgent(config_path="config/sources.json")
    raw_channels = scraper.run()
    if not raw_channels:
        logger.error("❌ Aucun flux récupéré par l'Agent 1. Arrêt du pipeline.")
        sys.exit(1)

    # 2. Agent 2 : Auditeur
    # Si nous tournons dans GitHub Actions ou localement, on ajuste la concurrence
    concurrency = int(os.environ.get("CONCURRENCY", 35))
    auditor = AuditorAgent(concurrency=concurrency, timeout=4.5)
    valid_channels = auditor.run(raw_channels)
    if not valid_channels:
        logger.error("❌ Aucune chaîne n'a passé l'audit de viabilité. Arrêt du pipeline.")
        sys.exit(1)

    # 3. Agent 3 : Déployeur & Organisateur
    base_url = os.environ.get("PAGES_BASE_URL", "https://psychokiller90.github.io/iptv-autopilot")
    publisher = PublisherAgent(output_dir="playlists", web_dir="web", base_url=base_url)
    stats = publisher.run(valid_channels)

    total_time = round(time.time() - start_time, 2)
    logger.info("=" * 65)
    logger.info(f"🎉 PIPELINE EXÉCUTÉ AVEC SUCCÈS EN {total_time}s !")
    logger.info(f"📊 Chaînes opérationnelles : {stats['total_valid']} / {len(raw_channels)}")
    logger.info(f"🇫🇷 Chaînes France : {stats['france_count']}")
    logger.info(f"🎬 Chaînes Cinéma : {stats['movies_count']}")
    logger.info(f"⚽ Chaînes Sports : {stats['sports_count']}")
    logger.info("=" * 65)

if __name__ == "__main__":
    main()
