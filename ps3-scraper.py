import requests
import pandas as pd
import time
import hashlib
import hmac
import xml.etree.ElementTree as ET
import json
import os
import sys
from pathlib import Path
import random
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
 
# Import Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium not available. Installing...")
    os.system("pip install selenium")
 
requests.packages.urllib3.disable_warnings()
 
class PS3TitlesScraper:
    """PS3 Titles scraper for SerialStation.com"""
 
    def __init__(self):
        self.base_url = "https://www.serialstation.com/titles/"
        self.params = {
            'so': 'tt',
            'systems': 'e80a9d68-aef2-4e23-8768-27ac0e5d9f25',  # PS3 system ID
            'title_id_type': 'BCES,BCUS,BLES,BLUS'  # PS3 title ID types
        }
        self.games_data = []
        self.driver = None
        self.setup_driver()
 
    def setup_driver(self):
        """Setup Chrome driver"""
        if not SELENIUM_AVAILABLE:
            print("❌ Selenium not available for scraping")
            return
 
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
 
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ Chrome driver initialized successfully")
        except Exception as e:
            print(f"❌ Error setting up driver: {e}")
            self.driver = None
 
    def scrape_page(self, page_num):
        """Scraper une page de titles PS3"""
        if not self.driver:
            print("❌ Chrome driver not available")
            return []
 
        # Construire l'URL pour cette page
        url = f"{self.base_url}?so={self.params['so']}&systems={self.params['systems']}&title_id_type={self.params['title_id_type']}&page={page_num}"
 
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"🔗 Loading PS3 page {page_num}...")
                self.driver.get(url)
 
                # Attendre que la page se charge
                time.sleep(3)
 
                # Trouver la table des titres
                tables = self.driver.find_elements(By.TAG_NAME, "table")
 
                if not tables:
                    print(f"❌ No table found on page {page_num}")
                    if attempt == max_retries - 1:
                        return []
                    time.sleep(5)
                    continue
 
                # Prendre la première table (principale)
                table = tables[0]
                rows = table.find_elements(By.TAG_NAME, "tr")
 
                if len(rows) <= 1:
                    print(f"❌ No data rows on page {page_num}")
                    if attempt == max_retries - 1:
                        return []
                    time.sleep(5)
                    continue
 
                page_games = []
 
                # Parcourir les lignes (sauf l'en-tête)
                for row_idx, row in enumerate(rows[1:], 1):
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
 
                        # Vérifier qu'on a au moins 3 colonnes (Title ID, Name, Editions)
                        if len(cells) >= 3:
                            title_id = cells[0].text.strip()
                            name = cells[1].text.strip()
                            editions = cells[2].text.strip()
 
                            if title_id and name:
                                # Nettoyer le Title ID (garder tel quel pour PS3)
                                game_data = {
                                    'Title_ID': title_id,
                                    'Name': name,
                                    'Editions': editions
                                }
                                page_games.append(game_data)
 
                    except Exception as e:
                        print(f"⚠️ Error parsing row {row_idx}: {e}")
                        continue
 
                print(f"✅ PS3 Page {page_num}: {len(page_games)} titles found")
                return page_games
 
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed for page {page_num}: {e}")
                if attempt == max_retries - 1:
                    return []
                time.sleep(random.uniform(3, 6))
 
        return []
 
    def scrape_all_titles(self, max_pages=33, start_page=1):
        """Scraper toutes les pages de titles PS3"""
        if start_page == 1:
            self.games_data = []
 
        # Charger les données existantes si on reprend
        if start_page > 1:
            try:
                df = pd.read_csv('ps3_titles_partial.csv')
                self.games_data = df.to_dict('records')
                print(f"📂 Resuming from page {start_page}, loaded {len(self.games_data)} existing titles")
            except FileNotFoundError:
                print("📂 No partial data found, starting fresh")
                self.games_data = []
 
        consecutive_empty_pages = 0
 
        print(f"🚀 Starting to scrape PS3 titles pages {start_page} to {max_pages}")
        print(f"🎯 Expected total: ~3,261 PS3 titles")
        print("=" * 60)
 
        start_time = time.time()
 
        for page in range(start_page, max_pages + 1):
            # Calculer le progrès
            progress = ((page - start_page + 1) / (max_pages - start_page + 1)) * 100
            elapsed = time.time() - start_time
            estimated_total = elapsed / (page - start_page + 1) * (max_pages - start_page + 1) if page > start_page else 0
            remaining = estimated_total - elapsed if page > start_page else 0
 
            print(f"\n📄 Page {page}/{max_pages} ({progress:.1f}%) - ETA: {remaining/60:.1f} min")
 
            page_data = self.scrape_page(page)
 
            if not page_data:
                consecutive_empty_pages += 1
                print(f"⚠️  Empty page {page} (consecutive: {consecutive_empty_pages})")
 
                if consecutive_empty_pages >= 5:
                    print(f"🛑 Hit {consecutive_empty_pages} consecutive empty pages, stopping")
                    break
            else:
                consecutive_empty_pages = 0
                self.games_data.extend(page_data)
                print(f"📊 Total PS3 titles collected: {len(self.games_data)}")
 
            # Sauvegarder tous les 10 pages (plus fréquent car moins de pages)
            if page % 10 == 0:
                self.save_to_csv('ps3_titles_partial.csv')
                print(f"💾 Saved checkpoint at page {page}")
 
            # Rate limiting
            time.sleep(random.uniform(1, 3))
 
        return self.games_data
 
    def save_to_csv(self, filename='ps3_titles.csv'):
        """Sauvegarder en CSV"""
        if self.games_data:
            try:
                df = pd.DataFrame(self.games_data)
                original_count = len(df)
 
                # Supprimer les doublons par Title_ID
                df = df.drop_duplicates(subset=['Title_ID'], keep='first')
                final_count = len(df)
 
                df.to_csv(filename, index=False, encoding='utf-8')
 
                if original_count != final_count:
                    print(f"💾 Saved {final_count} unique PS3 titles (removed {original_count - final_count} duplicates)")
                else:
                    print(f"💾 Saved {final_count} PS3 titles to {filename}")
 
                return final_count
            except Exception as e:
                print(f"❌ Error saving to CSV: {e}")
                return 0
        else:
            print("⚠️  No data to save")
            return 0
 
    def close_driver(self):
        """Fermer le driver"""
        if self.driver:
            self.driver.quit()
            print("🔒 Driver closed")
 
class PS3UpdateDownloader:
    """PS3 update downloader inspired by PySN"""
 
    def __init__(self, download_path='./ps3_titles_updates/'):
        self.download_path = Path(download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
 
    def request_update(self, title_id):
        """Request PS3 update info from Sony servers (inspired by PySN)"""
        try:
            # Clean title_id - Remove dashes for PS3
            title_id = title_id.strip().upper().replace('-', '')
 
            # PS3 uses simple URL structure (no HMAC like PS4/Vita)
            xml_url = f'https://a0.ww.np.dl.playstation.net/tpl/np/{title_id}/{title_id}-ver.xml'
 
            response = self.session.get(xml_url, stream=True, verify=False, timeout=30)
 
            if response.status_code == 200 and response.text:
                root = ET.fromstring(response.content)
                name_elem = root.find('./tag/package/paramsfo/')
                name = name_elem.text.replace('\n', ' ') if name_elem is not None else title_id
                return root, name
            elif response.status_code == 200 and response.text == '':
                return None, 'No updates available for'
            else:
                return None, 'Invalid ID'
        except Exception as e:
            return None, f"Error: {e}"
 
    def get_filename_from_url(self, url):
        """Extract filename from URL"""
        if not url:
            return "unknown_file.pkg"
 
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
 
        if not filename or not filename.endswith('.pkg'):
            path_parts = parsed.path.split('/')
            for part in reversed(path_parts):
                if '.pkg' in part:
                    filename = part
                    break
            else:
                filename = "ps3_update.pkg"
 
        return filename
 
    def get_update_info(self, title_id):
        """Get update information for a PS3 title (inspired by PySN)"""
        root, game_name = self.request_update(title_id)
 
        if root is None:
            return None
 
        updates = []
        versions_found = set()
 
        # Parcourir TOUS les packages (versions)
        for item in root.iter('package'):
            ver = item.get('version')
            url = item.get('url')
            sha1 = item.get('sha1sum')
            size = item.get('size')
 
            if url and ver:
                try:
                    update_info = {
                        'game_name': game_name,
                        'version': ver,
                        'url': url,
                        'hash': sha1,
                        'size': int(size) if size else 0,
                        'title_id': title_id,
                        'filename': self.get_filename_from_url(url),
                        'update_type': 'standard'
                    }
                    updates.append(update_info)
                    versions_found.add(ver)
 
                except Exception as e:
                    print(f"⚠️ Error parsing package for {title_id} v{ver}: {e}")
                    continue
 
        # Chercher aussi les DRM-Free updates (comme dans PySN)
        drm_free_updates = self.get_drm_free_updates(root, game_name, title_id)
        if drm_free_updates:
            updates.extend(drm_free_updates)
            for update in drm_free_updates:
                versions_found.add(update['version'])
 
        if updates:
            print(f"      📦 Found {len(versions_found)} versions, {len(updates)} files total")
 
        return updates if updates else None
 
    def get_drm_free_updates(self, root, game_name, title_id):
        """Get DRM-Free updates for PS3 (inspired by PySN)"""
        try:
            drm_free_updates = []
 
            # Check if there are URL elements (DRM-free updates)
            element_list = root.findall('.//')
            has_url_elements = any('url' in str(elem.tag) for elem in element_list)
 
            if has_url_elements:
                package_versions = []
                url_elements = []
 
                # Get package versions
                for item in root.iter('package'):
                    version = item.get('version')
                    if version:
                        package_versions.append(version)
 
                # Get URL elements
                for item in root.iter('url'):
                    url_elements.append({
                        'url': item.get('url'),
                        'sha1': item.get('sha1sum'),
                        'size': int(item.get('size')) if item.get('size') else 0
                    })
 
                # Match versions with URLs
                for i, version in enumerate(package_versions):
                    if i < len(url_elements):
                        url_data = url_elements[i]
                        if url_data['url']:
                            update_info = {
                                'game_name': game_name,
                                'version': version,
                                'url': url_data['url'],
                                'hash': url_data['sha1'],
                                'size': url_data['size'],
                                'title_id': title_id,
                                'filename': f"DRM-Free_{self.get_filename_from_url(url_data['url'])}",
                                'update_type': 'drm_free'
                            }
                            drm_free_updates.append(update_info)
 
            return drm_free_updates
 
        except Exception as e:
            print(f"⚠️ Error getting DRM-free updates for {title_id}: {e}")
            return []
 
    def process_single_title(self, title_data):
        """Process a single PS3 title and return update links"""
        title_id = title_data['Title_ID']
        title_name = title_data['Name']
        editions = title_data['Editions']
 
        try:
            print(f"🔍 Checking PS3 {title_id}...")
            updates = self.get_update_info(title_id)
 
            if updates:
                # Analyser les versions
                versions = {}
                total_size = 0
                standard_updates = []
                drm_free_updates = []
 
                for update in updates:
                    ver = update['version']
                    if ver not in versions:
                        versions[ver] = {'files': [], 'size': 0, 'types': set()}
 
                    versions[ver]['files'].append(update)
                    versions[ver]['types'].add(update['update_type'])
                    if update['size']:
                        versions[ver]['size'] += update['size']
                        total_size += update['size']
 
                    if update['update_type'] == 'standard':
                        standard_updates.append(update)
                    else:
                        drm_free_updates.append(update)
 
                # Trier les versions
                sorted_versions = sorted(versions.keys(), reverse=True)
                latest_version = sorted_versions[0] if sorted_versions else "Unknown"
 
                result = {
                    'title_id': title_id,
                    'title_name': title_name,
                    'sony_game_name': updates[0]['game_name'],
                    'editions': editions,
                    'has_updates': True,
                    'update_count': len(updates),
                    'version_count': len(versions),
                    'versions': sorted_versions,
                    'latest_version': latest_version,
                    'standard_updates_count': len(standard_updates),
                    'drm_free_updates_count': len(drm_free_updates),
                    'total_size_bytes': total_size,
                    'total_size_mb': total_size / (1024 * 1024),
                    'updates': updates,
                    'status': 'found'
                }
            else:
                result = {
                    'title_id': title_id,
                    'title_name': title_name,
                    'editions': editions,
                    'has_updates': False,
                    'update_count': 0,
                    'version_count': 0,
                    'status': 'no_updates'
                }
 
            return result
 
        except Exception as e:
            return {
                'title_id': title_id,
                'title_name': title_name,
                'editions': editions,
                'has_updates': False,
                'status': 'error',
                'error': str(e)
            }
 
    def batch_get_update_links(self, csv_file='ps3_titles.csv', max_workers=6, max_titles=None, chunk_size=500):
        """Get update links for all PS3 titles in CSV with chunked processing"""
        try:
            df = pd.read_csv(csv_file)
            if max_titles:
                df = df.head(max_titles)
 
            titles = df.to_dict('records')
            total_titles = len(titles)
 
            print(f"🚀 Starting PS3 update links collection for {total_titles:,} titles")
            print(f"📁 Results will be saved to: {self.download_path}")
            print(f"🔧 Using {max_workers} worker threads")
            print(f"📦 Processing in chunks of {chunk_size}")
            print("=" * 80)
 
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            return []
 
        all_results = []
        stats = {
            'total_titles': total_titles,
            'processed': 0,
            'found_updates': 0,
            'standard_updates': 0,
            'drm_free_updates': 0,
            'total_size_bytes': 0,
            'errors': 0
        }
 
        start_time = time.time()
 
        # Process in chunks to avoid memory issues
        for chunk_start in range(0, total_titles, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_titles)
            chunk_titles = titles[chunk_start:chunk_end]
 
            print(f"\n🔄 Processing chunk {chunk_start//chunk_size + 1}/{(total_titles-1)//chunk_size + 1}")
            print(f"   📋 Titles {chunk_start+1} to {chunk_end}")
 
            chunk_results = []
 
            # Process chunk with threading
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_title = {executor.submit(self.process_single_title, title): title for title in chunk_titles}
 
                for i, future in enumerate(as_completed(future_to_title), 1):
                    title = future_to_title[future]
 
                    try:
                        result = future.result()
                        chunk_results.append(result)
                        all_results.append(result)
 
                        stats['processed'] += 1
                        if result['has_updates']:
                            stats['found_updates'] += 1
                            stats['standard_updates'] += result.get('standard_updates_count', 0)
                            stats['drm_free_updates'] += result.get('drm_free_updates_count', 0)
                            stats['total_size_bytes'] += result.get('total_size_bytes', 0)
 
                        # Progress update
                        overall_progress = (stats['processed'] / total_titles) * 100
                        elapsed = time.time() - start_time
                        eta = (elapsed / stats['processed']) * (total_titles - stats['processed']) if stats['processed'] > 0 else 0
 
                        status_icon = "✅" if result['has_updates'] else "❌"
                        print(f"{status_icon} {stats['processed']:5d}/{total_titles} ({overall_progress:5.1f}%) - "
                              f"{result['title_id']} - {result['title_name'][:30]:<30} - "
                              f"ETA: {eta/60:.1f}m")
 
                        if result['has_updates']:
                            std_count = result.get('standard_updates_count', 0)
                            drm_count = result.get('drm_free_updates_count', 0)
                            version_info = f"{result['version_count']} versions" if result.get('version_count', 0) > 1 else f"v{result['latest_version']}"
                            print(f"      📦 {result['update_count']} files ({std_count} std, {drm_count} DRM-free), "
                                  f"{version_info}, {result['total_size_mb']:.1f} MB")
 
                    except Exception as e:
                        print(f"❌ Error processing {title['Title_ID']}: {e}")
                        stats['errors'] += 1
 
                    # Rate limiting (PS3 servers are older, be more gentle)
                    time.sleep(random.uniform(0.5, 1.5))
 
            # Save chunk progress
            self.save_progress(all_results, stats)
            print(f"💾 Chunk completed, {len(all_results)} total results saved")
 
        # Final save
        self.save_final_results(all_results, stats)
        self.print_final_stats(stats, time.time() - start_time)
 
        return all_results
 
    def save_progress(self, results, stats):
        """Save current progress"""
        if not results:
            return
 
        progress_file = self.download_path / "ps3_titles_update_links_progress.json"
        progress_file.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
 
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump({
                'stats': stats,
                'results_count': len(results),
                'last_processed': results[-1]['title_id'] if results else None
            }, f, indent=2, ensure_ascii=False)
 
    def save_final_results(self, results, stats):
        """Save final comprehensive results"""
        if not results:
            print("❌ No results to save")
            return
 
        # 1. Detailed JSON report (sample only for large datasets)
        if len(results) > 2000:
            sample_results = results[:500] + results[-500:]  # First and last 500
            detailed_file = self.download_path / "ps3_titles_sample_with_updates.json"
            with open(detailed_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'stats': stats,
                    'note': 'Sample of first and last 500 results due to file size',
                    'results': sample_results
                }, f, indent=2, ensure_ascii=False)
        else:
            detailed_file = self.download_path / "ps3_titles_with_updates.json"
            with open(detailed_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'stats': stats,
                    'results': results
                }, f, indent=2, ensure_ascii=False)
 
        # 2. Summary CSV
        summary_data = []
        for result in results:
            summary_data.append({
                'Title_ID': result['title_id'],
                'Title_Name': result['title_name'],
                'Sony_Game_Name': result.get('sony_game_name', ''),
                'Editions': result.get('editions', ''),
                'Has_Updates': result['has_updates'],
                'Update_Count': result.get('update_count', 0),
                'Version_Count': result.get('version_count', 0),
                'Standard_Updates': result.get('standard_updates_count', 0),
                'DRM_Free_Updates': result.get('drm_free_updates_count', 0),
                'Latest_Version': result.get('latest_version', ''),
                'Total_Size_MB': result.get('total_size_mb', 0),
                'Status': result['status']
            })
 
        summary_file = self.download_path / "ps3_titles_update_summary.csv"
        pd.DataFrame(summary_data).to_csv(summary_file, index=False, encoding='utf-8')
 
        # 3. Update links CSV (MOST IMPORTANT!)
        titles_with_updates = [r for r in results if r['has_updates']]
        if titles_with_updates:
            links_data = []
            for result in titles_with_updates:
                for update in result.get('updates', []):
                    links_data.append({
                        'Title_ID': result['title_id'],
                        'Title_Name': result['title_name'],
                        'Sony_Game_Name': result['sony_game_name'],
                        'Editions': result.get('editions', ''),
                        'Version': update['version'],
                        'Update_Type': update['update_type'],
                        'Size_MB': update['size'] / (1024 * 1024) if update['size'] else 0,
                        'Size_Bytes': update['size'],
                        'Filename': update['filename'],
                        'Download_URL': update['url'],
                        'SHA1_Hash': update['hash']
                    })
 
            links_file = self.download_path / "ps3_titles_download_links.csv"
            pd.DataFrame(links_data).to_csv(links_file, index=False, encoding='utf-8')
 
        # 4. Statistics CSV
        stats_data = [{
            'Total_Titles_Processed': stats['processed'],
            'Titles_With_Updates': stats['found_updates'],
            'Standard_Updates_Found': stats['standard_updates'],
            'DRM_Free_Updates_Found': stats['drm_free_updates'],
            'Total_Errors': stats['errors'],
            'Success_Rate_Percent': (stats['found_updates']/stats['processed'])*100 if stats['processed'] > 0 else 0,
            'Total_Update_Size_GB': stats['total_size_bytes']/(1024**3),
            'Average_Update_Size_MB': (stats['total_size_bytes']/stats['found_updates'])/(1024**2) if stats['found_updates'] > 0 else 0
        }]
 
        stats_file = self.download_path / "ps3_titles_statistics.csv"
        pd.DataFrame(stats_data).to_csv(stats_file, index=False, encoding='utf-8')
 
        print(f"\n📊 Results saved:")
        print(f"   📄 Detailed data: {detailed_file}")
        print(f"   📊 Summary: {summary_file}")
        print(f"   📈 Statistics: {stats_file}")
        if titles_with_updates:
            print(f"   🔗 Download links: {links_file}")
 
    def print_final_stats(self, stats, duration):
        """Print final statistics"""
        print(f"\n" + "=" * 80)
        print(f"🎉 PS3 TITLES UPDATE LINKS COLLECTION COMPLETED!")
        print(f"=" * 80)
        print(f"⏱️  Duration: {duration/3600:.1f} hours")
        print(f"🎮 Total titles processed: {stats['processed']:,}")
        print(f"📦 Titles with updates: {stats['found_updates']:,}")
        print(f"📋 Standard updates: {stats['standard_updates']:,}")
        print(f"🆓 DRM-Free updates: {stats['drm_free_updates']:,}")
        print(f"❌ Errors: {stats['errors']:,}")
        if stats['processed'] > 0:
            print(f"📈 Success rate: {(stats['found_updates']/stats['processed'])*100:.1f}%")
        print(f"💾 Total update size: {stats['total_size_bytes']/(1024**3):.2f} GB")
 
        if stats['found_updates'] > 0:
            avg_size = (stats['total_size_bytes'] / stats['found_updates']) / (1024**2)
            print(f"📊 Average update size: {avg_size:.1f} MB per title")
 
def print_banner():
    """Print application banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║           PS3 Titles Scraper & Update Tool                ║
    ║              SerialStation.com - PS3 Section              ║
    ║              3,261 PS3 Titles on 33 Pages                ║
    ║             With Sony Update Links Collection             ║
    ║               (Standard + DRM-Free Updates)               ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)
 
def print_menu():
    """Print main menu"""
    menu = """
    📋 Main Menu:
    ┌─────────────────────────────────────────────────────────────┐
    │ 1. 🕷️  Start full PS3 titles scraping (33 pages)           │
    │ 2. ⏭️  Resume PS3 titles scraping from last position       │
    │ 3. 📂 Load existing PS3 titles CSV data                    │
    │ 4. 🔍 Search for PS3 updates by Title ID                   │
    │ 5. 🔗 Get update links for first 25 titles (test)         │
    │ 6. 📦 Get update links for ALL PS3 titles (~3k)           │
    │ 7. 📊 Show statistics from loaded data                     │
    │ 8. 🧪 Test scraping on page 1 of PS3 titles               │
    │ 9. 🚪 Exit                                                 │
    └─────────────────────────────────────────────────────────────┘
    """
    print(menu)
 
def main():
    """Main CLI application"""
    print_banner()
 
    # N'initialiser le scraper que si nécessaire
    scraper = None
    downloader = PS3UpdateDownloader()
    titles_data = []
 
    try:
        while True:
            print_menu()
 
            try:
                choice = input("Enter your choice (1-9): ").strip()
 
                if choice in ['1', '2', '8']:
                    # Options qui nécessitent Selenium
                    if not SELENIUM_AVAILABLE:
                        print("❌ Selenium not available. Please install: pip install selenium")
                        continue
 
                    if scraper is None:
                        scraper = PS3TitlesScraper()
                        if not scraper.driver:
                            print("❌ Could not initialize Chrome driver. Please check your installation.")
                            continue
 
                if choice == '1':
                    print("\n🚀 Starting full scrape of PS3 Titles...")
                    print("🎯 Target: 3,261 PS3 titles across 33 pages")
                    print("⚠️  This will take ~1-2 hours to complete!")
                    print("💡 The script will save progress every 10 pages and can be resumed later.")
                    confirm = input("Continue? (y/N): ").strip().lower()
 
                    if confirm == 'y':
                        start_time = time.time()
                        titles_data = scraper.scrape_all_titles(max_pages=33)
                        final_count = scraper.save_to_csv('ps3_titles.csv')
 
                        end_time = time.time()
                        duration = end_time - start_time
                        print(f"\n✅ PS3 titles scraping complete in {duration/3600:.1f} hours!")
                        print(f"📊 Total unique PS3 titles found: {final_count:,}")
 
                elif choice == '2':
                    try:
                        df = pd.read_csv('ps3_titles_partial.csv')
                        # Estimer la page basée sur le nombre de titres (~100 par page)
                        last_page = len(df) // 100 + 1
 
                        print(f"\n⏭️  Resuming from approximately page {last_page}")
                        print(f"📊 Currently have {len(df):,} PS3 titles in partial data")
                        confirm = input("Continue? (y/N): ").strip().lower()
 
                        if confirm == 'y':
                            titles_data = scraper.scrape_all_titles(max_pages=33, start_page=last_page)
                            final_count = scraper.save_to_csv('ps3_titles.csv')
                            print(f"\n✅ Scraping complete! Total unique PS3 titles: {final_count:,}")
 
                    except FileNotFoundError:
                        print("❌ No partial data found. Use option 1 to start fresh.")
 
                elif choice == '3':
                    try:
                        csv_files = ['ps3_titles.csv', 'ps3_titles_partial.csv', 'ps3_titles_test.csv']
                        csv_file = None
 
                        for file in csv_files:
                            if os.path.exists(file):
                                csv_file = file
                                break
 
                        if csv_file:
                            df = pd.read_csv(csv_file)
                            titles_data = df.to_dict('records')
                            print(f"\n✅ Loaded {len(titles_data):,} PS3 titles from {csv_file}")
 
                            # Show sample
                            print("\n📋 Sample PS3 titles:")
                            print("-" * 80)
                            print(f"{'Title_ID':<15} {'Name':<40} {'Editions':<25}")
                            print("-" * 80)
                            for i, title in enumerate(titles_data[:5]):
                                name = title['Name'][:37] + '...' if len(title['Name']) > 40 else title['Name']
                                editions = title['Editions'][:22] + '...' if len(title['Editions']) > 25 else title['Editions']
                                print(f"{title['Title_ID']:<15} {name:<40} {editions:<25}")
                            if len(titles_data) > 5:
                                print(f"\n... and {len(titles_data) - 5:,} more PS3 titles")
                        else:
                            print("❌ No CSV files found. Scrape PS3 titles first.")
 
                    except Exception as e:
                        print(f"❌ Error loading CSV: {e}")
 
                elif choice == '4':
                    title_id = input("\n🔍 Enter PS3 Title ID (e.g., BLES12345): ").strip().upper()
                    if title_id:
                        print(f"\n🔍 Searching for updates for {title_id}...")
                        updates = downloader.get_update_info(title_id)
 
                        if updates:
                            print(f"\n✅ Found {len(updates)} updates for {title_id}:")
                            print("=" * 60)
 
                            for i, update in enumerate(updates):
                                size_mb = update['size'] / (1024 * 1024) if update['size'] else 0
                                update_type = "🆓 DRM-Free" if update['update_type'] == 'drm_free' else "📦 Standard"
                                print(f"\nUpdate {i+1} {update_type}:")
                                print(f"  🎮 Game: {update['game_name']}")
                                print(f"  📦 Version: {update['version']}")
                                print(f"  📏 Size: {size_mb:.1f} MB")
                                print(f"  📁 Filename: {update['filename']}")
                                print(f"  🔗 URL: {update['url']}")
                                print(f"  🔐 Hash: {update['hash']}")
                        else:
                            print(f"❌ No updates found for {title_id}")
 
                elif choice == '5':
                    print("\n🔗 Getting update links for first 25 PS3 titles (test)...")
                    csv_files = ['ps3_titles_test.csv', 'ps3_titles.csv', 'ps3_titles_partial.csv']
                    csv_file = None
 
                    for file in csv_files:
                        if os.path.exists(file):
                            csv_file = file
                            print(f"📁 Found CSV file: {csv_file}")
                            break
 
                    if csv_file:
                        confirm = input("Continue with update links collection for first 25 PS3 titles? (y/N): ").strip().lower()
 
                        if confirm == 'y':
                            results = downloader.batch_get_update_links(csv_file, max_workers=4, max_titles=25)
                            with_updates = [r for r in results if r['has_updates']]
                            std_updates = sum(r.get('standard_updates_count', 0) for r in with_updates)
                            drm_updates = sum(r.get('drm_free_updates_count', 0) for r in with_updates)
                            print(f"\n✅ Test completed! Found updates for {len(with_updates)}/25 PS3 titles")
                            print(f"📦 Updates found: {std_updates} standard, {drm_updates} DRM-free")
                    else:
                        print("❌ No CSV file found. Please scrape PS3 titles first.")
 
                elif choice == '6':
                    csv_files = ['ps3_titles.csv', 'ps3_titles_partial.csv']
                    csv_file = None
 
                    for file in csv_files:
                        if os.path.exists(file):
                            csv_file = file
                            break
 
                    if not csv_file:
                        print("❌ No CSV file found. Please scrape PS3 titles first.")
                        continue
 
                    df = pd.read_csv(csv_file)
                    print(f"\n📦 Getting update links for ALL {len(df):,} PS3 titles...")
                    print("🎯 This is the complete PS3 titles database!")
                    print("⚠️  This will take ~3-6 hours to complete!")
                    print("🔗 Only links will be collected, no downloads")
                    print("💾 Progress will be saved regularly")
                    print("🆓 Will find both standard AND DRM-free updates")
                    confirm = input("Continue? (y/N): ").strip().lower()
 
                    if confirm == 'y':
                        results = downloader.batch_get_update_links(csv_file, max_workers=6, chunk_size=300)
 
                        with_updates = [r for r in results if r['has_updates']]
                        total_size_gb = sum(r.get('total_size_bytes', 0) for r in with_updates) / (1024**3)
                        std_updates = sum(r.get('standard_updates_count', 0) for r in with_updates)
                        drm_updates = sum(r.get('drm_free_updates_count', 0) for r in with_updates)
 
                        print(f"\n🎉 COMPLETE PS3 DATABASE COLLECTION FINISHED!")
                        print(f"   ✅ Titles with updates: {len(with_updates):,}/{len(df):,}")
                        print(f"   📦 Standard updates: {std_updates:,}")
                        print(f"   🆓 DRM-Free updates: {drm_updates:,}")
                        print(f"   💾 Total size available: {total_size_gb:.2f} GB")
                        print(f"   📁 Results saved in: {downloader.download_path}")
 
                elif choice == '7':
                    if titles_data:
                        print(f"\n📊 PS3 Titles Statistics:")
                        print("=" * 40)
                        print(f"Total PS3 titles: {len(titles_data):,}")
 
                        # Analyze title ID prefixes
                        prefixes = {}
                        for title in titles_data:
                            title_id = title.get('Title_ID', '')
                            if len(title_id) >= 4:
                                prefix = title_id[:4]
                                prefixes[prefix] = prefixes.get(prefix, 0) + 1
 
                        print(f"\n📋 Title ID Prefixes:")
                        for prefix, count in sorted(prefixes.items(), key=lambda x: x[1], reverse=True):
                            print(f"  {prefix}: {count:,}")
 
                        # Analyze editions
                        editions_count = {}
                        for title in titles_data:
                            editions = title.get('Editions', 'Unknown').split(',')
                            for edition in editions:
                                edition = edition.strip()
                                editions_count[edition] = editions_count.get(edition, 0) + 1
 
                        print(f"\n📋 Top 10 Edition Types:")
                        for edition, count in sorted(editions_count.items(), key=lambda x: x[1], reverse=True)[:10]:
                            print(f"  {edition}: {count:,}")
 
                    else:
                        print("❌ No data loaded. Load CSV first or scrape new data.")
 
                elif choice == '8':
                    print("\n🧪 Testing PS3 titles scraping on page 1...")
                    titles = scraper.scrape_page(1)
 
                    if titles:
                        print(f"\n✅ Test successful! Found {len(titles)} PS3 titles on page 1")
                        print("\n📋 Sample PS3 titles:")
                        print("-" * 80)
                        print(f"{'Title_ID':<15} {'Name':<40} {'Editions':<25}")
                        print("-" * 80)
                        for i, title in enumerate(titles[:5]):
                            name = title['Name'][:37] + '...' if len(title['Name']) > 40 else title['Name']
                            editions = title['Editions'][:22] + '...' if len(title['Editions']) > 25 else title['Editions']
                            print(f"{title['Title_ID']:<15} {name:<40} {editions:<25}")
 
                        # Option pour sauvegarder
                        save_test = input(f"\n💾 Save these {len(titles)} PS3 titles as test CSV? (y/N): ").strip().lower()
                        if save_test == 'y':
                            df = pd.DataFrame(titles)
                            df.to_csv('ps3_titles_test.csv', index=False, encoding='utf-8')
                            print(f"✅ Saved to ps3_titles_test.csv")
                    else:
                        print("❌ Test failed! No PS3 titles found on page 1")
 
                elif choice == '9':
                    print("\n👋 Exiting...")
                    break
 
                else:
                    print("❌ Invalid choice. Please enter 1-9.")
 
            except KeyboardInterrupt:
                print("\n\n⚠️  Operation cancelled by user")
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
 
            input("\nPress Enter to continue...")
            print("\n" + "="*60)
 
    finally:
        if scraper:
            scraper.close_driver()
 
if __name__ == "__main__":
    main()