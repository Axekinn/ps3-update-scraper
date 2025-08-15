# 🎮 PS3 Titles Scraper & Update Tool
 
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Selenium](https://img.shields.io/badge/selenium-4.0+-green.svg)](https://selenium-python.readthedocs.io/)
 
A comprehensive tool for scraping PS3 game titles from SerialStation.com and collecting their update download links directly from Sony's servers. This tool extracts information for all **3,261 PS3 titles** and finds both **standard** and **DRM-free** update packages.

I'm already providing the result, and I'm including the scripts in case you want to do it yourself and Sony changes something in the future, or if you want to improve the script.
The difference between ps3_updatesv1 and ps3_updates is that I modified the script in the meantime because it seemed strange to me to have so few updates.

So v1 is what was originally released (I lost the original script), and without v1, this is what it is today with the script that goes with it.
I can't be bothered to understand why, etc., but in any case, the result in ps3_downloads.json was exactly the same, so at any given time, the two versions of the scripts are exactly the same, just put differently.

Feel free to rack your brains over it.
I created this script because I wanted to download everything at once, and I couldn't be bothered to do it one ID at a time (with [PySN](https://github.com/AphelionWasTaken/PySN/tree/main)), so I did it to select everything at once and download it (hence the ps3_downloads).
You can go to ps3_downloads, copy everything, and paste the download links into [Jdownloader](https://jdownloader.org/jdownloader2), which will retrieve and install everything. 
 
![PS3 Scraper Demo](https://img.shields.io/badge/Status-Active-brightgreen)
 
## 🌟 Features
 
### 📋 Title Scraping
- **Complete PS3 Database**: Scrapes all 3,261 PS3 titles across 33 pages
- **Smart Resume**: Continue scraping from where you left off
- **Progress Tracking**: Auto-saves every 10 pages with detailed progress reports
- **Data Validation**: Removes duplicates and validates Title IDs
 
### 🔗 Update Collection
- **Sony Server Integration**: Direct communication with PlayStation update servers
- **Dual Update Types**: Finds both standard and DRM-free updates
- **Comprehensive Metadata**: Extracts versions, file sizes, SHA1 hashes, and download URLs
- **Batch Processing**: Efficient multi-threaded processing with rate limiting
- **Progress Saving**: Regular checkpoints with detailed statistics
 
### 📊 Data Export
- **Multiple Formats**: CSV, JSON exports with different detail levels
- **Download Links**: Ready-to-use download URLs for all updates
- **Statistics Reports**: Comprehensive analysis of the PS3 catalog
- **Sample Data**: Optimized file sizes for large datasets
 
## 🚀 Quick Start
 
### Prerequisites
 
```bash
# Install Python dependencies
pip install requests pandas selenium
 
# Install Chrome/Chromium browser (for Selenium)
# Ubuntu/Debian:
sudo apt-get install chromium-browser
 
# Or download Chrome manually from https://google.com/chrome
```
 
### Installation
 
```bash
git clone https://github.com/Axekinn/ps3-update-scraper.git
cd ps3-scraper
pip install -r requirements.txt
```
 
### Basic Usage
 
```bash
python ps3-scraper.py
```
 
## 📖 Usage Guide
 
### 🎯 Main Menu Options
 
```
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
```
 
### 🏃‍♂️ Quick Test
 
Start with option **8** to test scraping functionality:
```bash
# Tests scraping on page 1 (fastest way to verify setup)
python ps3-scraper.py
# Choose option 8
```
 
### 📦 Full Database Collection
 
For the complete PS3 catalog:
```bash
# 1. First scrape all titles (1-2 hours)
python ps3-scraper.py
# Choose option 1
 
# 2. Then collect all update links (3-6 hours)
# Choose option 6
```
 
### 🔍 Search Individual Titles
 
```bash
# Search for updates for a specific game
python ps3-scraper.py
# Choose option 4
# Enter: BLES00826 (for example)
```
 
## 📁 Output Files
 
The tool generates several output files in the `./ps3_titles_updates/` directory:
 
### 📊 CSV Files
- **`ps3_titles.csv`** - Complete PS3 titles database
- **`ps3_titles_download_links.csv`** - ⭐ **MAIN OUTPUT** - All download links
- **`ps3_titles_update_summary.csv`** - Summary statistics per title
- **`ps3_titles_statistics.csv`** - Global statistics
 
### 📋 JSON Files
- **`ps3_titles_with_updates.json`** - Detailed results (complete or sample)
- **`ps3_titles_update_links_progress.json`** - Progress tracking
 
### 📈 Example Download Links Output
 
| Title_ID | Title_Name | Sony_Game_Name | Version | Update_Type | Size_MB | Download_URL | SHA1_Hash |
|----------|------------|----------------|---------|-------------|---------|--------------|-----------|
| BLES00826 | Uncharted: Drake's Fortune | UNCHARTED | 1.01 | standard | 45.2 | https://... | abc123... |
| BLES00826 | Uncharted: Drake's Fortune | UNCHARTED | 1.01 | drm_free | 45.2 | https://... | def456... |
 
## 🔧 Configuration
 
### 🎛️ Scraping Settings
 
```python
# In ps3-scraper.py, you can modify:
max_pages = 33          # Total pages to scrape
max_workers = 6         # Concurrent threads for updates
chunk_size = 300        # Titles processed per chunk
rate_limit = (0.5, 1.5) # Delay between requests (seconds)
```
 
### 🌐 Proxy Support
 
```python
# Add proxy configuration in session setup:
session.proxies = {
    'http': 'http://proxy:port',
    'https': 'https://proxy:port'
}
```
 
## 📊 Expected Results
 
### 📈 Database Statistics
- **Total PS3 Titles**: ~3,261
- **Titles with Updates**: ~60-70%
- **Average Updates per Title**: 2-3
- **Total Update Files**: ~6,000-8,000
- **Combined Size**: ~500-800 GB
 
### 🕐 Performance
- **Title Scraping**: 1-2 hours (33 pages)
- **Update Collection**: 3-6 hours (3,261 titles)
- **Memory Usage**: ~200-500 MB peak
- **Storage**: ~50-100 MB for all data files
 
## 🛠️ Technical Details
 
### 🏗️ Architecture
 
```
PS3TitlesScraper
├── Selenium WebDriver (Chrome)
├── SerialStation.com scraping
└── CSV/JSON export
 
PS3UpdateDownloader
├── Sony PlayStation servers
├── Multi-threaded processing
├── Progress tracking
└── Comprehensive reporting
```
 
### 🔌 APIs Used
 
- **SerialStation.com**: PS3 titles catalog
- **Sony PlayStation Network**: Update XML endpoints
- **Chrome WebDriver**: Dynamic content scraping
 
### 📦 Dependencies
 
```txt
requests>=2.25.0
pandas>=1.3.0
selenium>=4.0.0
lxml>=4.6.0
```
 
## 🚨 Important Notes
 
### ⚖️ Legal & Ethical Use
- This tool is for **educational and archival purposes**
- Respects rate limits and server resources
- **Does not download copyrighted content**
- Only collects publicly available metadata and links
 
### 🛡️ Rate Limiting
- Built-in delays between requests
- Conservative threading limits
- Automatic retry logic
- Server-friendly request patterns
 
### 💾 Data Persistence
- Auto-saves progress every 10 pages
- Resume capability for interrupted sessions
- Multiple export formats
- Backup and recovery options
 
## 🎯 Use Cases
 
### 🔬 Research & Analysis
- PS3 game catalog analysis
- Update distribution patterns
- File size and version tracking
- Regional release differences
 
### 📚 Archival & Preservation
- Complete PS3 metadata collection
- Update availability tracking
- Historical version documentation
- Digital preservation efforts
 
### 🛠️ Development & Testing
- PS3 homebrew development
- Update system analysis
- Network protocol research
- Batch download automation
 
## 🤝 Contributing
 
We welcome contributions! Here's how you can help:
 
1. **🐛 Bug Reports**: Found an issue? Open an issue with details
2. **💡 Feature Requests**: Have an idea? Let's discuss it
3. **🔧 Code Contributions**: Fork, modify, and submit a PR
4. **📖 Documentation**: Help improve the docs
 
### 🔄 Development Setup
 
```bash
git clone https://github.com/Axekinn/ps3-update-scraper.git
cd ps3-scraper
pip install -r requirements-dev.txt
```
 
## 📜 License
 
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
 
## ⚠️ Disclaimer
 
This tool is provided for educational and research purposes only. Users are responsible for complying with applicable laws and terms of service. The authors do not condone piracy or copyright infringement.
 
## 🙋‍♂️ Support
 
- **📧 Issues**: [GitHub Issues](https://github.com/Axekinn/ps3-update-scraper/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/Axekinn/ps3-update-scraper/discussions)
- **📖 Wiki**: [Project Wiki](https://github.com/Axekinn/ps3-update-scraper/wiki)
 
## 🎉 Acknowledgments
 
- **SerialStation.com** for maintaining the PS3 titles database
- **Sony PlayStation** for the update server infrastructure
- **Selenium WebDriver** team for the automation framework
- **Python community** for the excellent libraries
 
---
 
<div align="center">
  <b>⭐ Star this repo if you find it useful! ⭐</b>
  <br><br>
  Made with ❤️ for the PS3 community
</div>
