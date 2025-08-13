#!/usr/bin/env python3
"""
PlayStation 3 Update Scraper
Scrape tous les jeux PS3 depuis renascene.com et récupère leurs mises à jour
"""

import json
import requests
import xml.etree.ElementTree as ET
import hashlib
import hmac
import concurrent.futures
import time
import logging
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ps3_update_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class UpdateInfo:
    """Data class for update information"""
    console: str
    title_id: str
    game_name: str
    version: str
    download_url: str
    file_size: int
    sha1_hash: str
    update_type: str = "standard"
    region: str = "Unknown"

@dataclass
class GameInfo:
    """Data class for game information from renascene"""
    ex: str
    title_id: str
    region: str
    title: str
    folder: str
    disc_id: str
    nfo: str
    released: str
    street: str
    nuke: str
    size: str
    type: str

class PS3UpdateScraper:
    """Scraper pour les mises à jour PS3"""
    
    def __init__(self, max_workers: int = 5, timeout: int = 30):
        self.max_workers = max_workers
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Chemin du script pour sauvegarder le JSON au même endroit
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

    def scrape_renascene_games(self, max_pages: int = 41) -> List[GameInfo]:
        """Scrape tous les jeux PS3 depuis renascene.com"""
        games = []
        
        logger.info(f"Scraping {max_pages} pages de renascene.com...")
        
        for page in range(1, max_pages + 1):
            try:
                url = f"https://renascene.com/ps3/?target=list&ord=desc&page={page}"
                logger.info(f"Scraping page {page}/{max_pages}")
                
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Trouver la table des jeux
                table = soup.find('table', class_='table')
                if not table:
                    logger.warning(f"Aucune table trouvée sur la page {page}")
                    continue
                
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    try:
                        cols = row.find_all('td')
                        if len(cols) >= 12:  # S'assurer qu'on a toutes les colonnes
                            # Extraire toutes les informations selon l'ordre spécifié
                            # EX	ID	REGION	TITLE	FOLDER	DISC ID		NFO	RELEASED	STREET	NUKE	SIZE	TYPE
                            
                            ex = cols[0].get_text(strip=True)
                            title_id = cols[1].get_text(strip=True)
                            region = cols[2].get_text(strip=True)
                            title = cols[3].get_text(strip=True)
                            folder = cols[4].get_text(strip=True)
                            disc_id = cols[5].get_text(strip=True)
                            # cols[6] semble être vide d'après votre description
                            nfo = cols[7].get_text(strip=True)
                            released = cols[8].get_text(strip=True)
                            street = cols[9].get_text(strip=True)
                            nuke = cols[10].get_text(strip=True)
                            size = cols[11].get_text(strip=True)
                            
                            # Pour TYPE, vérifier s'il y a une 13ème colonne
                            game_type = cols[12].get_text(strip=True) if len(cols) > 12 else ""
                            
                            # Valider le format du title_id PS3
                            if re.match(r'^[A-Z]{4}\d{5}$', title_id):
                                games.append(GameInfo(
                                    ex=ex,
                                    title_id=title_id,
                                    region=region,
                                    title=title,
                                    folder=folder,
                                    disc_id=disc_id,
                                    nfo=nfo,
                                    released=released,
                                    street=street,
                                    nuke=nuke,
                                    size=size,
                                    type=game_type
                                ))
                            else:
                                logger.debug(f"Format title_id invalide: {title_id}")
                                
                    except Exception as e:
                        logger.warning(f"Erreur lors du parsing d'une ligne sur la page {page}: {e}")
                        continue
                
                # Pause entre les pages pour éviter la surcharge du serveur
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Erreur lors du scraping de la page {page}: {e}")
                continue
        
        logger.info(f"Total de {len(games)} jeux PS3 trouvés")
        return games

    def build_ps3_update_url(self, title_id: str) -> str:
        """Construire l'URL de mise à jour PS3"""
        return f'https://a0.ww.np.dl.playstation.net/tpl/np/{title_id}/{title_id}-ver.xml'

    def fetch_url_content(self, url: str) -> Optional[bytes]:
        """Récupérer le contenu d'une URL avec gestion d'erreur"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.content if response.content else None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Échec de récupération {url}: {e}")
            return None

    def parse_ps3_update(self, game_info: GameInfo) -> List[UpdateInfo]:
        """Parser les mises à jour PS3 pour un jeu"""
        updates = []
        url = self.build_ps3_update_url(game_info.title_id)
        
        content = self.fetch_url_content(url)
        if not content:
            return updates
        
        try:
            root = ET.fromstring(content)
            
            # Récupérer le nom du jeu depuis le XML ou utiliser celui de renascene
            game_name_elem = root.find('.//tag/package/paramsfo')
            if game_name_elem is not None and game_name_elem.text:
                game_name = game_name_elem.text.replace('\n', ' ').strip()
            else:
                game_name = game_info.title
            
            # Parser les mises à jour standard
            for package in root.iter('package'):
                version = package.get('version', 'Unknown')
                download_url = package.get('url', '')
                sha1_hash = package.get('sha1sum', '')
                size = int(package.get('size', 0))
                
                if download_url:
                    updates.append(UpdateInfo(
                        console='PlayStation 3',
                        title_id=game_info.title_id,
                        game_name=game_name,
                        version=version,
                        download_url=download_url,
                        file_size=size,
                        sha1_hash=sha1_hash,
                        update_type='standard',
                        region=game_info.region
                    ))
            
            # Parser les mises à jour DRM-free
            for url_elem in root.iter('url'):
                if url_elem.get('url'):
                    parent = url_elem.getparent()
                    version = parent.get('version', 'Unknown') if parent is not None else 'Unknown'
                    
                    updates.append(UpdateInfo(
                        console='PlayStation 3',
                        title_id=game_info.title_id,
                        game_name=game_name,
                        version=f"{version} (DRM-Free)",
                        download_url=url_elem.get('url'),
                        file_size=int(url_elem.get('size', 0)),
                        sha1_hash=url_elem.get('sha1sum', ''),
                        update_type='drm_free',
                        region=game_info.region
                    ))
                    
        except ET.ParseError as e:
            logger.debug(f"Erreur de parsing XML pour {game_info.title_id}: {e}")
        
        return updates

    def scrape_single_game(self, game_info: GameInfo) -> List[UpdateInfo]:
        """Scraper les mises à jour pour un seul jeu"""
        logger.debug(f"Scraping des mises à jour pour {game_info.title_id} - {game_info.title}")
        return self.parse_ps3_update(game_info)

    def scrape_all_updates(self, games: List[GameInfo]) -> List[Dict]:
        """Scraper toutes les mises à jour en utilisant le traitement concurrent"""
        all_updates = []
        successful_games = 0
        
        logger.info(f"Début du scraping des mises à jour pour {len(games)} jeux...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Soumettre toutes les tâches
            future_to_game = {
                executor.submit(self.scrape_single_game, game): game
                for game in games
            }
            
            # Traiter les résultats au fur et à mesure
            for i, future in enumerate(concurrent.futures.as_completed(future_to_game), 1):
                game_info = future_to_game[future]
                try:
                    updates = future.result()
                    if updates:
                        all_updates.extend([update.__dict__ for update in updates])
                        successful_games += 1
                        logger.info(f"[{i}/{len(games)}] {len(updates)} mises à jour trouvées pour {game_info.title_id} - {game_info.title}")
                    else:
                        logger.debug(f"[{i}/{len(games)}] Aucune mise à jour pour {game_info.title_id}")
                        
                except Exception as e:
                    logger.error(f"[{i}/{len(games)}] Erreur pour {game_info.title_id}: {e}")
                
                # Afficher le progrès tous les 50 jeux
                if i % 50 == 0:
                    logger.info(f"Progression: {i}/{len(games)} jeux traités, {len(all_updates)} mises à jour trouvées")
        
        logger.info(f"Scraping terminé: {successful_games}/{len(games)} jeux avec mises à jour, {len(all_updates)} mises à jour totales")
        return all_updates

    def save_to_json(self, updates: List[Dict], games: List[GameInfo], filename: str = None) -> str:
        """Sauvegarder les mises à jour dans un fichier JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ps3_updates_{timestamp}.json"
        
        # Sauvegarder dans le même répertoire que le script
        output_path = os.path.join(self.script_dir, filename)
        
        output_data = {
            "scrape_date": datetime.now().isoformat(),
            "total_games_scraped": len(games),
            "total_updates_found": len(updates),
            "games_with_updates": len(set(update['title_id'] for update in updates)),
            "updates": updates
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Sauvegardé {len(updates)} mises à jour dans {output_path}")
        return output_path

    def save_games_list(self, games: List[GameInfo], filename: str = None) -> str:
        """Sauvegarder la liste des jeux dans un fichier JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ps3_games_list_{timestamp}.json"
        
        # Sauvegarder dans le même répertoire que le script
        output_path = os.path.join(self.script_dir, filename)
        
        games_data = {
            "scrape_date": datetime.now().isoformat(),
            "total_games": len(games),
            "games": [game.__dict__ for game in games]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(games_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Sauvegardé {len(games)} jeux dans {output_path}")
        return output_path

def main():
    """Fonction principale"""
    logger.info("=== PlayStation 3 Update Scraper ===")
    
    # Initialiser le scraper
    scraper = PS3UpdateScraper(max_workers=5, timeout=30)
    
    try:
        # Étape 1: Scraper la liste des jeux depuis renascene
        logger.info("Étape 1: Récupération de la liste des jeux PS3...")
        games = scraper.scrape_renascene_games(max_pages=41)
        
        if not games:
            logger.error("Aucun jeu trouvé. Arrêt du script.")
            return
        
        # Sauvegarder la liste des jeux
        games_file = scraper.save_games_list(games)
        
        # Étape 2: Scraper les mises à jour pour tous les jeux
        logger.info("Étape 2: Récupération des mises à jour...")
        updates = scraper.scrape_all_updates(games)
        
        # Étape 3: Sauvegarder les résultats
        logger.info("Étape 3: Sauvegarde des résultats...")
        output_file = scraper.save_to_json(updates, games)
        
        # Résumé final
        logger.info("=== RÉSUMÉ FINAL ===")
        logger.info(f"Jeux PS3 trouvés: {len(games)}")
        logger.info(f"Jeux avec mises à jour: {len(set(update['title_id'] for update in updates))}")
        logger.info(f"Total des mises à jour: {len(updates)}")
        logger.info(f"Liste des jeux sauvegardée: {games_file}")
        logger.info(f"Mises à jour sauvegardées: {output_file}")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrompu par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        raise

if __name__ == "__main__":
    main()