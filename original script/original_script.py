#!/usr/bin/env python3
"""
PlayStation Console Update Scraper
Scrapes update data for PS3, PS4, and PS Vita consoles and outputs structured JSON data.
"""

import json
import requests
import xml.etree.ElementTree as ET
import hashlib
import hmac
import concurrent.futures
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
        logging.FileHandler('update_scraper.log'),
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
    release_date: str
    download_url: str
    file_size: int
    sha1_hash: str
    update_type: str = "standard"

class PlayStationUpdateScraper:
    """Main scraper class for PlayStation console updates"""
    
    def __init__(self, max_workers: int = 10, timeout: int = 30):
        self.max_workers = max_workers
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Console-specific configuration
        self.ps_vita_key = bytearray.fromhex('E5E278AA1EE34082A088279C83F9BBC806821C52F2AB5D2B4ABD995450355114')
        self.ps4_key = bytearray.fromhex('AD62E37F905E06BC19593142281C112CEC0E7EC3E97EFDCAEFCDBAAFA6378D84')
        
        self.firmware_locales = {
            'PlayStation 3': ['us', 'eu', 'jp', 'kr', 'uk', 'mx', 'au', 'sa', 'tw', 'ru', 'br'],
            'PlayStation 4': ['us', 'eu', 'jp', 'kr', 'uk', 'mx', 'au', 'sa', 'tw', 'ru', 'cn', 'br'],
            'PlayStation Vita': ['us', 'eu', 'jp', 'kr', 'uk', 'mx', 'au', 'sa', 'tw', 'ru', 'cn']
        }

    def generate_auth_hash(self, title_id: str, console: str) -> str:
        """Generate authentication hash for PS4 and PS Vita"""
        id_bytes = bytes(f'np_{title_id}', 'UTF-8')
        
        if console == 'PlayStation Vita':
            return hmac.new(self.ps_vita_key, id_bytes, hashlib.sha256).hexdigest()
        elif console == 'PlayStation 4':
            return hmac.new(self.ps4_key, id_bytes, hashlib.sha256).hexdigest()
        
        return ""

    def build_update_url(self, title_id: str, console: str) -> str:
        """Build the update XML URL for different consoles"""
        if console == 'PlayStation 3':
            return f'https://a0.ww.np.dl.playstation.net/tpl/np/{title_id}/{title_id}-ver.xml'
        
        auth_hash = self.generate_auth_hash(title_id, console)
        
        if console == 'PlayStation Vita':
            return f'https://gs-sec.ww.np.dl.playstation.net/pl/np/{title_id}/{auth_hash}/{title_id}-ver.xml'
        elif console == 'PlayStation 4':
            return f'https://gs-sec.ww.np.dl.playstation.net/plo/np/{title_id}/{auth_hash}/{title_id}-ver.xml'
        
        return ""

    def fetch_url_content(self, url: str, is_json: bool = False) -> Optional[any]:
        """Fetch content from URL with error handling"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            if not response.content:
                return None
                
            if is_json:
                return response.json()
            
            return response.content
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def parse_ps3_update(self, title_id: str) -> List[UpdateInfo]:
        """Parse PS3 game updates"""
        updates = []
        url = self.build_update_url(title_id, 'PlayStation 3')
        
        content = self.fetch_url_content(url)
        if not content:
            return updates
        
        try:
            root = ET.fromstring(content)
            
            # Get game name
            game_name_elem = root.find('.//tag/package/paramsfo/')
            game_name = game_name_elem.text.replace('\n', ' ').strip() if game_name_elem is not None else title_id
            
            # Parse standard updates
            for package in root.iter('package'):
                version = package.get('version', 'Unknown')
                download_url = package.get('url', '')
                sha1_hash = package.get('sha1sum', '')
                size = int(package.get('size', 0))
                
                if download_url:
                    updates.append(UpdateInfo(
                        console='PlayStation 3',
                        title_id=title_id,
                        game_name=game_name,
                        version=version,
                        release_date='Unknown',
                        download_url=download_url,
                        file_size=size,
                        sha1_hash=sha1_hash,
                        update_type='standard'
                    ))
            
            # Parse DRM-free updates
            for url_elem in root.iter('url'):
                if url_elem.get('url'):
                    parent_package = url_elem.find('..')
                    version = parent_package.get('version', 'Unknown') if parent_package is not None else 'Unknown'
                    
                    updates.append(UpdateInfo(
                        console='PlayStation 3',
                        title_id=title_id,
                        game_name=game_name,
                        version=f"{version} (DRM-Free)",
                        release_date='Unknown',
                        download_url=url_elem.get('url'),
                        file_size=int(url_elem.get('size', 0)),
                        sha1_hash=url_elem.get('sha1sum', ''),
                        update_type='drm_free'
                    ))
                    
        except ET.ParseError as e:
            logger.error(f"XML parsing error for {title_id}: {e}")
        
        return updates

    def parse_ps4_update(self, title_id: str) -> List[UpdateInfo]:
        """Parse PS4 game updates"""
        updates = []
        url = self.build_update_url(title_id, 'PlayStation 4')
        
        content = self.fetch_url_content(url)
        if not content:
            return updates
        
        try:
            root = ET.fromstring(content)
            
            # Get game name
            game_name_elem = root.find('.//tag/package/paramsfo/')
            game_name = game_name_elem.text.replace('\n', ' ').strip() if game_name_elem is not None else title_id
            
            for package in root.iter('package'):
                version = package.get('version', 'Unknown')
                manifest_url = package.get('manifest_url', '')
                
                if manifest_url:
                    manifest_data = self.fetch_url_content(manifest_url, is_json=True)
                    if manifest_data and 'pieces' in manifest_data:
                        for piece in manifest_data['pieces']:
                            download_url = piece.get('url', '')
                            sha1_hash = piece.get('hashValue', '')
                            size = piece.get('fileSize', 0)
                            
                            if download_url:
                                updates.append(UpdateInfo(
                                    console='PlayStation 4',
                                    title_id=title_id,
                                    game_name=game_name,
                                    version=version,
                                    release_date='Unknown',
                                    download_url=download_url,
                                    file_size=size,
                                    sha1_hash=sha1_hash
                                ))
                                
        except ET.ParseError as e:
            logger.error(f"XML parsing error for {title_id}: {e}")
        
        return updates

    def parse_vita_update(self, title_id: str) -> List[UpdateInfo]:
        """Parse PS Vita game updates"""
        updates = []
        url = self.build_update_url(title_id, 'PlayStation Vita')
        
        content = self.fetch_url_content(url)
        if not content:
            return updates
        
        try:
            root = ET.fromstring(content)
            
            # Get game name
            game_name_elem = root.find('.//tag/package/paramsfo/')
            game_name = game_name_elem.text.replace('\n', ' ').strip() if game_name_elem is not None else title_id
            
            for package in root.iter('package'):
                version = package.get('version', 'Unknown')
                download_url = package.get('url', '')
                sha1_hash = package.get('sha1sum', '')
                size = int(package.get('size', 0))
                
                if download_url:
                    updates.append(UpdateInfo(
                        console='PlayStation Vita',
                        title_id=title_id,
                        game_name=game_name,
                        version=version,
                        release_date='Unknown',
                        download_url=download_url,
                        file_size=size,
                        sha1_hash=sha1_hash
                    ))
                    
        except ET.ParseError as e:
            logger.error(f"XML parsing error for {title_id}: {e}")
        
        return updates

    def parse_firmware_updates(self, console: str) -> List[UpdateInfo]:
        """Parse firmware updates for consoles"""
        updates = []
        locales = self.firmware_locales.get(console, [])
        
        for locale in locales:
            try:
                if console == 'PlayStation 3':
                    url = f'https://f{locale}01.ps3.update.playstation.net/update/ps3/list/{locale}/ps3-updatelist.txt'
                    content = self.fetch_url_content(url)
                    
                    if content:
                        soup = BeautifulSoup(content.decode('utf-8'), 'html.parser')
                        text = soup.get_text().split(';')
                        
                        version = region = download_url = ""
                        for item in text:
                            if 'CompatibleSystemSoftwareVersion' in item:
                                version = item[32:36]
                            elif item.startswith('# '):
                                region = item[2:4].upper()
                                if region == 'SO':
                                    region = 'SA'
                            elif 'UPDAT.PUP' in item:
                                download_url = item[4:].strip()
                                break
                        
                        if download_url and version:
                            # Get file size
                            size = self.get_file_size(download_url)
                            
                            updates.append(UpdateInfo(
                                console=console,
                                title_id=region,
                                game_name=f"{console} Firmware",
                                version=version,
                                release_date='Unknown',
                                download_url=download_url,
                                file_size=size,
                                sha1_hash='N/A'
                            ))
                
                else:  # PS4 or PS Vita
                    if console == 'PlayStation 4':
                        url = f'https://f{locale}01.ps4.update.playstation.net/update/ps4/list/{locale}/ps4-updatelist.xml'
                    else:
                        url = f'https://f{locale}01.psp2.update.playstation.net/update/psp2/list/{locale}/psp2-updatelist.xml'
                    
                    content = self.fetch_url_content(url)
                    if content:
                        root = ET.fromstring(content)
                        
                        for image in root.iter('image'):
                            size = int(image.get('size', 0))
                            download_url = ''.join(image.itertext()).strip()
                            
                            # Remove trailing characters
                            if download_url.endswith('/UPDAT.PUP'):
                                download_url = download_url[:-8]
                            
                            region_elem = root.find('.//region')
                            region = region_elem.get('id', '').upper() if region_elem is not None else locale.upper()
                            
                            if console == 'PlayStation Vita':
                                version_elem = root.find('.//version')
                                update_type_elem = root.find('.//update_data')
                            else:
                                version_elem = root.find('.//system_pup')
                                update_type_elem = root.find('.//update_data')
                            
                            version = version_elem.get('label', 'Unknown') if version_elem is not None else 'Unknown'
                            update_type = update_type_elem.get('update_type', 'firmware') if update_type_elem is not None else 'firmware'
                            
                            if download_url:
                                updates.append(UpdateInfo(
                                    console=console,
                                    title_id=region,
                                    game_name=f"{console} {update_type.title()}",
                                    version=version,
                                    release_date='Unknown',
                                    download_url=download_url,
                                    file_size=size,
                                    sha1_hash='N/A'
                                ))
                                
            except Exception as e:
                logger.error(f"Error parsing firmware for {console} locale {locale}: {e}")
                continue
        
        return updates

    def get_file_size(self, url: str) -> int:
        """Get file size from URL headers"""
        try:
            response = self.session.head(url, timeout=self.timeout)
            return int(response.headers.get('Content-Length', 0))
        except:
            return 0

    def scrape_title_updates(self, title_id: str, console: str) -> List[UpdateInfo]:
        """Scrape updates for a specific title"""
        logger.info(f"Scraping {console} updates for {title_id}")
        
        if console == 'PlayStation 3':
            return self.parse_ps3_update(title_id)
        elif console == 'PlayStation 4':
            return self.parse_ps4_update(title_id)
        elif console == 'PlayStation Vita':
            return self.parse_vita_update(title_id)
        
        return []

    def scrape_all_updates(self, title_list: List[Dict[str, str]], include_firmware: bool = True) -> List[Dict]:
        """Scrape all updates using concurrent processing"""
        all_updates = []
        
        # Scrape game updates concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_title = {
                executor.submit(self.scrape_title_updates, item['title_id'], item['console']): item
                for item in title_list
            }
            
            for future in concurrent.futures.as_completed(future_to_title):
                title_info = future_to_title[future]
                try:
                    updates = future.result()
                    all_updates.extend([update.__dict__ for update in updates])
                    logger.info(f"Found {len(updates)} updates for {title_info['title_id']}")
                except Exception as e:
                    logger.error(f"Error scraping {title_info['title_id']}: {e}")
        
        # Scrape firmware updates if requested
        if include_firmware:
            for console in ['PlayStation 3', 'PlayStation 4', 'PlayStation Vita']:
                try:
                    fw_updates = self.parse_firmware_updates(console)
                    all_updates.extend([update.__dict__ for update in fw_updates])
                    logger.info(f"Found {len(fw_updates)} firmware updates for {console}")
                except Exception as e:
                    logger.error(f"Error scraping firmware for {console}: {e}")
        
        return all_updates

    def save_to_json(self, updates: List[Dict], filename: str = None) -> str:
        """Save updates to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"playstation_updates_{timestamp}.json"
        
        output_data = {
            "scrape_date": datetime.now().isoformat(),
            "total_updates": len(updates),
            "updates": updates
        }
        
        output_path = Path(filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(updates)} updates to {output_path}")
        return str(output_path)

def load_title_list(file_path: str) -> List[Dict[str, str]]:
    """Load title list from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Handle different JSON formats
        if isinstance(data, list):
            return data
        elif 'titles' in data:
            return data['titles']
        else:
            logger.error("Invalid JSON format. Expected list or object with 'titles' key")
            return []
            
    except FileNotFoundError:
        logger.error(f"Title list file not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in title list file: {e}")
        return []

def main():
    """Main function"""
    # Example title list - replace with your actual data source
    title_list = [
        {"title_id": "BLUS30181", "console": "PlayStation 3"},
        {"title_id": "CUSA00127", "console": "PlayStation 4"},
        {"title_id": "PCSE00024", "console": "PlayStation Vita"},
        # Add more titles as needed
    ]
    
    # You can also load from a JSON file:
    # title_list = load_title_list("title_list.json")
    
    # Initialize scraper
    scraper = PlayStationUpdateScraper(max_workers=5, timeout=30)
    
    try:
        # Scrape all updates
        logger.info("Starting PlayStation update scraping...")
        updates = scraper.scrape_all_updates(title_list, include_firmware=True)
        
        # Save results
        output_file = scraper.save_to_json(updates)
        logger.info(f"Scraping completed. Results saved to {output_file}")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()