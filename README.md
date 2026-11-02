# 🚀 IPTV Autopilot • Système Multi-Agents Autonome

[![IPTV Multi-Agent Autopilot](https://github.com/psychokiller90/iptv-autopilot/actions/workflows/update_streams.yml/badge.svg)](https://github.com/psychokiller90/iptv-autopilot/actions/workflows/update_streams.yml)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Dashboard-3b82f6?logo=github)](https://psychokiller90.github.io/iptv-autopilot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Android TV](https://img.shields.io/badge/Android%20TV-Televizo%20%7C%20TiviMate%20%7C%20VLC-10b981?logo=android)](https://psychokiller90.github.io/iptv-autopilot)

Pipeline autonome d'agents IA conçu pour **explorer GitHub**, **auditer les flux vidéos HLS en temps réel** et **distribuer des listes IPTV 100 % opérationnelles** directement sur votre Box TV.

---

## 📺 Liens Permanents pour votre Box TV (Televizo)

Copiez simplement l'une de ces adresses directes dans votre lecteur IPTV. Les listes s'actualisent automatiquement sans jamais nécessiter de changer l'adresse :

| Thématique | Description | Lien Direct pour Televizo |
| :--- | :--- | :--- |
| 🇫🇷 **France & TNT** | Chaînes françaises vérifiées (TNT, régionales, séries) | `https://psychokiller90.github.io/iptv-autopilot/playlists/france.m3u` |
| 🎬 **Cinéma & Films** | Chaînes cinéma, films d'action, SF, thriller | `https://psychokiller90.github.io/iptv-autopilot/playlists/cinema.m3u` |
| ⚽ **Sports** | Chaînes et événements sportifs en direct | `https://psychokiller90.github.io/iptv-autopilot/playlists/sports.m3u` |
| 📺 **Séries** | Séries TV et fictions en diffusion continue | `https://psychokiller90.github.io/iptv-autopilot/playlists/series.m3u` |
| 📰 **Actualités** | Chaînes d'information en continu | `https://psychokiller90.github.io/iptv-autopilot/playlists/news.m3u` |
| 🌐 **Toutes les Chaînes** | Agrégation globale mondiale | `https://psychokiller90.github.io/iptv-autopilot/playlists/all.m3u` |

👉 **Accéder au Dashboard Web interactif :** [https://psychokiller90.github.io/iptv-autopilot](https://psychokiller90.github.io/iptv-autopilot)

---

## 🏛️ Les 3 Agents en Action

```mermaid
graph LR
    A1["🕵️ Agent 1\nScraper"] -->|Flux bruts| A2["🔬 Agent 2\nAuditeur HLS"]
    A2 -->|Flux 100% testés| A3["🚀 Agent 3\nDéployeur & Pages"]
    A3 -->|Mise à jour 12h| TV["📺 Box Android (Televizo)"]
```

### 1. 🕵️ Agent 1 : Le Scraper (`agents/scraper.py`)
* Moissonne les dépôts de référence (`iptv-org`, `dcmp`, `free-tv`, `ParaTV`...).
* Explore l'API Search de GitHub pour découvrir de nouveaux dépôts publics.
* Normalise les noms, catégories (`group-title`), pays et logos.

### 2. 🔬 Agent 2 : L'Auditeur Haute Cadence (`agents/auditor.py`)
* Audit asynchrone multi-threadé (`aiohttp`).
* Vérification en deux étapes :
  1. Validité du fichier manifest `.m3u8` (rejet immédiat des faux positifs HTML code 200).
  2. Téléchargement partiel du **premier segment vidéo réel** (`.ts`/`.m4s`) pour garantir l'absence d'erreurs 403 / 404 / 500.
* Calcul de la latence de réponse en millisecondes.

### 3. 🚀 Agent 3 : Le Déployeur & Organisateur (`agents/publisher.py`)
* Génère les fichiers M3U modulaires par thématique et par pays.
* Produit le rapport d'audit détaillé `AUDIT_REPORT.md`.
* Construit le portail Web interactif déployé sur **GitHub Pages**.

---

## 🕹️ Avoir la main sur vos Agents en ligne

Vous pouvez piloter vos agents à tout moment sans aucun terminal :

1. **Forcer une mise à jour immédiate :**
   * Rendez-vous dans l'onglet **[Actions](https://github.com/psychokiller90/iptv-autopilot/actions)**.
   * Sélectionnez **IPTV Multi-Agent Autopilot** à gauche.
   * Cliquez sur **Run workflow** > **Run workflow**.
2. **Ajouter de nouvelles sources :**
   * Modifiez le fichier `config/sources.json` directement depuis l'interface web de GitHub.
   * Vos agents prendront automatiquement en compte les nouvelles adresses au prochain passage !
3. **Mettre en pause les agents :**
   * Dans l'onglet **Actions**, cliquez sur les trois petits points `...` à côté du workflow et choisissez **Disable workflow**.

---

## 🛠️ Lancement en Local (Optionnel)

Si vous souhaitez exécuter le pipeline sur votre ordinateur :

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer le pipeline
python run_pipeline.py
```

---

*Développé avec ❤️ pour une expérience TV fluide et sans écrans noirs.*
