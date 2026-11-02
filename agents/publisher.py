import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger("PublisherAgent")

class PublisherAgent:
    """Agent 3 : Organisateur modulaire, exportateur M3U et générateur de dashboard web."""

    def __init__(self, output_dir: str = "playlists", web_dir: str = "web", base_url: str = ""):
        self.output_dir = output_dir
        self.web_dir = web_dir
        self.base_url = base_url.rstrip("/")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(f"{self.output_dir}/countries", exist_ok=True)
        os.makedirs(self.web_dir, exist_ok=True)

    def run(self, channels: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info("🚀 Démarrage de l'Agent 3 (Déployeur & Organisateur)...")
        now = datetime.now()
        timestamp_str = now.strftime("%d/%m/%Y à %H:%M:%S")

        # 1. Tri et partitionnement des chaînes
        france_channels = [c for c in channels if c.get("country") == "FR"]
        movies_channels = [c for c in channels if c.get("group") == "Movies"]
        sports_channels = [c for c in channels if c.get("group") == "Sports"]
        series_channels = [c for c in channels if c.get("group") == "Series"]
        news_channels = [c for c in channels if c.get("group") == "News"]
        music_channels = [c for c in channels if c.get("group") == "Music"]
        kids_channels = [c for c in channels if c.get("group") == "Kids"]

        # Partitionnement par pays
        countries_dict = {}
        for c in channels:
            country = c.get("country", "GLOBAL")
            countries_dict.setdefault(country, []).append(c)

        # 2. Génération de la sélection Box TV (France + Toutes les thématiques Cinéma, Sports, Séries, News, etc.)
        tv_box_dict = {}
        for c in (france_channels + movies_channels + sports_channels + series_channels + news_channels + kids_channels + music_channels):
            tv_box_dict[c["url"]] = c
        tv_box_channels = list(tv_box_dict.values())

        # 3. Génération des fichiers M3U modulaires
        self._write_m3u(f"{self.output_dir}/tv_box.m3u", tv_box_channels, "IPTV Box TV - Sélection Complète")
        self._write_m3u(f"{self.output_dir}/all.m3u", channels, "IPTV Global - 100% Validé")
        self._write_m3u(f"{self.output_dir}/france.m3u", france_channels, "IPTV France & Francophonie")
        self._write_m3u(f"{self.output_dir}/cinema.m3u", movies_channels, "IPTV Cinéma & Films")
        self._write_m3u(f"{self.output_dir}/sports.m3u", sports_channels, "IPTV Sports")
        self._write_m3u(f"{self.output_dir}/series.m3u", series_channels, "IPTV Séries & Fictions")
        self._write_m3u(f"{self.output_dir}/news.m3u", news_channels, "IPTV Informations")
        self._write_m3u(f"{self.output_dir}/music.m3u", music_channels, "IPTV Musique")
        self._write_m3u(f"{self.output_dir}/kids.m3u", kids_channels, "IPTV Jeunesse & Animation")

        for country_code, c_list in countries_dict.items():
            if country_code not in ("GLOBAL", "ALL") and len(c_list) >= 2:
                self._write_m3u(f"{self.output_dir}/countries/{country_code.lower()}.m3u", c_list, f"IPTV {country_code}")

        # 4. Génération du rapport Markdown
        stats = {
            "timestamp": timestamp_str,
            "total_valid": len(channels),
            "tv_box_count": len(tv_box_channels),
            "france_count": len(france_channels),
            "movies_count": len(movies_channels),
            "sports_count": len(sports_channels),
            "series_count": len(series_channels),
            "news_count": len(news_channels),
            "music_count": len(music_channels),
            "kids_count": len(kids_channels),
            "countries_count": len(countries_dict)
        }

        self._generate_report(stats, channels[:20])

        # 4. Génération du Dashboard Web HTML
        self._generate_web_dashboard(stats)

        # 5. Notification Telegram (si configurée)
        self._send_telegram_notification(stats)

        logger.info(f"✅ Déploiement terminé : {len(channels)} chaînes réparties dans {self.output_dir}/")
        return stats

    def _send_telegram_notification(self, stats: Dict[str, Any]):
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            return

        text = (
            "🚀 <b>IPTV Autopilot • Rapport d'Actualisation</b>\n\n"
            f"📅 <b>Date :</b> {stats['timestamp']}\n"
            f"🟢 <b>Total flux opérationnels :</b> <b>{stats['total_valid']}</b>\n\n"
            "📊 <b>Détails par catégorie :</b>\n"
            f"• 🇫🇷 <b>France & TNT :</b> {stats['france_count']} chaînes\n"
            f"• 🎬 <b>Cinéma & Films :</b> {stats['movies_count']} chaînes\n"
            f"• ⚽ <b>Sports :</b> {stats['sports_count']} chaînes\n"
            f"• 📺 <b>Séries :</b> {stats['series_count']} chaînes\n"
            f"• 📰 <b>Actualités :</b> {stats['news_count']} chaînes\n\n"
            "📺 <i>Votre Box TV est à jour !</i>\n"
            f"🌐 <a href=\"{self.base_url or 'https://psychokiller90.github.io/iptv-autopilot'}\">Ouvrir le Dashboard Web</a>"
        )
        try:
            import urllib.request
            payload = json.dumps({
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }).encode("utf-8")
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info("📱 Notification Telegram envoyée avec succès.")
        except Exception as e:
            logger.warning(f"⚠️ Échec notification Telegram : {e}")



    def _write_m3u(self, filepath: str, channels: List[Dict[str, Any]], title: str):
        lines = [f"#EXTM3U name=\"{title}\""]
        for ch in channels:
            extinf = f'#EXTINF:-1 tvg-id="{ch.get("tvg_id", "")}" tvg-name="{ch.get("tvg_name", ch["name"])}" tvg-logo="{ch.get("logo", "")}" group-title="{ch.get("group", "General")}",{ch["name"]}'
            lines.append(extinf)
            ua = ch.get("user_agent")
            if ua and "Mozilla" in ua:
                lines.append(f'#EXTVLCOPT:http-user-agent={ua}')
            lines.append(ch["url"])

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _generate_report(self, stats: Dict[str, Any], sample_channels: List[Dict[str, Any]]):
        content = f"""# 📊 Rapport d'Audit IPTV Autopilot

**Dernière exécution :** {stats['timestamp']}  
**Chaînes 100 % opérationnelles :** 🟢 **{stats['total_valid']} flux vérifiés**  

---

## 📁 Répartition par Catégorie

| Module | Fichier M3U | Nombre de Chaînes Actives |
| :--- | :--- | :---: |
| 🇫🇷 **France & TNT** | `playlists/france.m3u` | 🟢 **{stats['france_count']}** |
| 🎬 **Cinéma & Films** | `playlists/cinema.m3u` | 🟢 **{stats['movies_count']}** |
| ⚽ **Sports** | `playlists/sports.m3u` | 🟢 **{stats['sports_count']}** |
| 📺 **Séries & Fictions** | `playlists/series.m3u` | 🟢 **{stats['series_count']}** |
| 📰 **Actualités & Infos** | `playlists/news.m3u` | 🟢 **{stats['news_count']}** |
| 🎵 **Musique** | `playlists/music.m3u` | 🟢 **{stats['music_count']}** |
| 👶 **Jeunesse & Dessins Animés** | `playlists/kids.m3u` | 🟢 **{stats['kids_count']}** |
| 🌐 **Toutes les Chaînes** | `playlists/all.m3u` | 🟢 **{stats['total_valid']}** |

---

## ⚡ Échantillon des Flux Actifs

| Chaîne | Catégorie | Pays | Latence |
| :--- | :--- | :---: | :---: |
"""
        for c in sample_channels:
            content += f"| {c['name']} | {c.get('group', 'General')} | {c.get('country', 'ALL')} | {c.get('latency_ms', 0)} ms |\n"

        with open("AUDIT_REPORT.md", "w", encoding="utf-8") as f:
            f.write(content)

    def _generate_web_dashboard(self, stats: Dict[str, Any]):
        base = self.base_url or "https://psychokiller90.github.io/iptv-autopilot"
        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPTV Autopilot Dashboard | Flux 100% Vérifiés</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #090d16;
            --card-bg: rgba(22, 30, 49, 0.7);
            --border: rgba(255, 255, 255, 0.08);
            --primary: #3b82f6;
            --primary-glow: rgba(59, 130, 246, 0.35);
            --success: #10b981;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Outfit', sans-serif;
            background: radial-gradient(circle at 50% 0%, #1e293b 0%, var(--bg) 100%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.4rem 1rem;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: var(--success);
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }}
        .badge-dot {{
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.4; transform: scale(0.85); }}
        }}
        h1 {{
            font-size: 2.75rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.75rem;
            background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        p.subtitle {{
            color: var(--text-muted);
            font-size: 1.1rem;
            max-width: 600px;
            margin: 0 auto;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.5rem;
        }}
        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
        }}
        .stat-val {{
            font-size: 2.25rem;
            font-weight: 800;
            color: var(--primary);
            line-height: 1;
            margin-bottom: 0.5rem;
        }}
        .stat-lbl {{
            color: var(--text-muted);
            font-size: 0.9rem;
            font-weight: 500;
        }}
        .playlists-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
        }}
        .playlist-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 1.25rem;
            padding: 1.75rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            backdrop-filter: blur(12px);
            transition: all 0.25s ease;
        }}
        .playlist-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(59, 130, 246, 0.4);
            box-shadow: 0 12px 24px -10px var(--primary-glow);
        }}
        .card-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }}
        .card-title {{
            font-size: 1.35rem;
            font-weight: 700;
        }}
        .card-count {{
            background: rgba(255, 255, 255, 0.05);
            padding: 0.25rem 0.75rem;
            border-radius: 0.5rem;
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--primary);
        }}
        .card-desc {{
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
            line-height: 1.4;
        }}
        .card-actions {{
            display: flex;
            gap: 0.75rem;
        }}
        .btn {{
            flex: 1;
            padding: 0.75rem 1rem;
            border-radius: 0.75rem;
            font-family: inherit;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            text-align: center;
            text-decoration: none;
            transition: all 0.2s;
            border: none;
        }}
        .btn-primary {{
            background: var(--primary);
            color: #fff;
        }}
        .btn-primary:hover {{
            background: #2563eb;
            box-shadow: 0 4px 12px var(--primary-glow);
        }}
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.06);
            color: var(--text-main);
            border: 1px solid var(--border);
        }}
        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.12);
        }}
        .toast {{
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--success);
            color: #000;
            padding: 0.75rem 1.5rem;
            border-radius: 0.75rem;
            font-weight: 700;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
            box-shadow: 0 10px 25px rgba(16, 185, 129, 0.4);
        }}
        .toast.show {{
            opacity: 1;
            transform: translateY(0);
        }}
        footer {{
            text-align: center;
            margin-top: 4rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="badge">
                <span class="badge-dot"></span>
                Système Multi-Agents En Ligne
            </div>
            <h1>IPTV Autopilot</h1>
            <p class="subtitle">Scraping continu GitHub, audit HLS haute cadence & synchronisation Box TV automatique toutes les 12 heures.</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-val">{stats['total_valid']}</div>
                <div class="stat-lbl">Flux 100% Opérationnels</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">{stats['france_count']}</div>
                <div class="stat-lbl">Chaînes France & TNT</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">{stats['movies_count']}</div>
                <div class="stat-lbl">Cinéma & Films</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">12h</div>
                <div class="stat-lbl">Fréquence d'actualisation</div>
            </div>
        </div>

        <div class="playlists-grid">
            <!-- TV Box Selection Card -->
            <div class="playlist-card" style="border-color: rgba(59, 130, 246, 0.6); background: rgba(30, 58, 138, 0.25);">
                <div>
                    <div class="card-top">
                        <div class="card-title">🌟 Sélection Complète Box TV</div>
                        <div class="card-count" style="color: #60a5fa; background: rgba(59, 130, 246, 0.2);">{stats.get('tv_box_count', stats['total_valid'])} flux</div>
                    </div>
                    <div class="card-desc">Le pack ultime pour votre Box : Toutes les chaînes françaises + Cinéma, Sports, Séries, Infos, Jeunesse et Musique triés dans des catégories dédiées.</div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary" onclick="copyUrl('{base}/playlists/tv_box.m3u')">Copier le lien</button>
                    <a class="btn btn-secondary" href="{base}/playlists/tv_box.m3u" download>Télécharger</a>
                </div>
            </div>

            <!-- France Card -->
            <div class="playlist-card">
                <div>
                    <div class="card-top">
                        <div class="card-title">🇫🇷 France & TNT</div>
                        <div class="card-count">{stats['france_count']} flux</div>
                    </div>
                    <div class="card-desc">Toutes les chaînes françaises vérifiées (TNT nationale, chaînes régionales, informations et fictions). Idéal pour votre Box.</div>
                </div>

                <div class="card-actions">
                    <button class="btn btn-primary" onclick="copyUrl('{base}/playlists/france.m3u')">Copier le lien</button>
                    <a class="btn btn-secondary" href="{base}/playlists/france.m3u" download>Télécharger</a>
                </div>
            </div>

            <!-- Cinema Card -->
            <div class="playlist-card">
                <div>
                    <div class="card-top">
                        <div class="card-title">🎬 Cinéma & Films</div>
                        <div class="card-count">{stats['movies_count']} flux</div>
                    </div>
                    <div class="card-desc">Chaînes dédiées au cinéma, films d'action, science-fiction, thrillers et rétrospectives.</div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary" onclick="copyUrl('{base}/playlists/cinema.m3u')">Copier le lien</button>
                    <a class="btn btn-secondary" href="{base}/playlists/cinema.m3u" download>Télécharger</a>
                </div>
            </div>

            <!-- Sports Card -->
            <div class="playlist-card">
                <div>
                    <div class="card-top">
                        <div class="card-title">⚽ Sports</div>
                        <div class="card-count">{stats['sports_count']} flux</div>
                    </div>
                    <div class="card-desc">Flux de sports actifs, compétitions, chaînes fédérales et actualités sportives en direct.</div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary" onclick="copyUrl('{base}/playlists/sports.m3u')">Copier le lien</button>
                    <a class="btn btn-secondary" href="{base}/playlists/sports.m3u" download>Télécharger</a>
                </div>
            </div>

            <!-- Series Card -->
            <div class="playlist-card">
                <div>
                    <div class="card-top">
                        <div class="card-title">📺 Séries & Fictions</div>
                        <div class="card-count">{stats['series_count']} flux</div>
                    </div>
                    <div class="card-desc">Chaînes thématiques diffusant des séries 24h/24 sans interruption.</div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary" onclick="copyUrl('{base}/playlists/series.m3u')">Copier le lien</button>
                    <a class="btn btn-secondary" href="{base}/playlists/series.m3u" download>Télécharger</a>
                </div>
            </div>

            <!-- News Card -->
            <div class="playlist-card">
                <div>
                    <div class="card-top">
                        <div class="card-title">📰 Actualités</div>
                        <div class="card-count">{stats['news_count']} flux</div>
                    </div>
                    <div class="card-desc">Chaînes d'information en continu (France 24, BFM, Euronews, etc.) mondiales et francophones.</div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary" onclick="copyUrl('{base}/playlists/news.m3u')">Copier le lien</button>
                    <a class="btn btn-secondary" href="{base}/playlists/news.m3u" download>Télécharger</a>
                </div>
            </div>

            <!-- All Card -->
            <div class="playlist-card">
                <div>
                    <div class="card-top">
                        <div class="card-title">🌐 Playlist Globale</div>
                        <div class="card-count">{stats['total_valid']} flux</div>
                    </div>
                    <div class="card-desc">L'intégralité des flux fonctionnels découverts à travers le monde, triés par catégories et logos.</div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary" onclick="copyUrl('{base}/playlists/all.m3u')">Copier le lien</button>
                    <a class="btn btn-secondary" href="{base}/playlists/all.m3u" download>Télécharger</a>
                </div>
            </div>
        </div>

        <footer>
            <p>Dernier audit automatique : {stats['timestamp']} • Hébergé gratuitement sur GitHub Pages</p>
        </footer>
    </div>

    <div id="toast" class="toast">Lien copié dans le presse-papier !</div>

    <script>
        function copyUrl(url) {{
            navigator.clipboard.writeText(url).then(() => {{
                const toast = document.getElementById('toast');
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 2500);
            }});
        }}
    </script>
</body>
</html>
"""
        with open(f"{self.web_dir}/index.html", "w", encoding="utf-8") as f:
            f.write(html)
        # Copier également à la racine pour GitHub Pages si nécessaire
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)

if __name__ == "__main__":
    pub = PublisherAgent()
    pub.run([
        {"name": "France 2", "url": "https://fake/fr2.m3u8", "group": "General", "country": "FR", "latency_ms": 35},
        {"name": "Ciné Action", "url": "https://fake/cine.m3u8", "group": "Movies", "country": "FR", "latency_ms": 42}
    ])
