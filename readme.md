# PS3 Update Scraper

Scraper that:
- Fetches the list of PS3 releases from Renascene (41 pages).
- Resolves valid PS3 Title IDs (BLES/BLUS/BCES/BCUS/BLJM/BLJS/NPxx) from columns, NFO pages, and row links.
- Queries Sony’s endpoint for each Title ID and parses ver.xml files.
- Produces a consolidated JSON with available updates.

Many titles never had a patch: 404s on ver.xml are therefore frequent and normal.

I'm already providing the result, and I'm including the scripts in case you want to do it yourself and Sony changes something in the future, or if you want to improve the script.
The difference between ps3_updatesv1 and ps3_updates is that I modified the script in the meantime because it seemed strange to me to have so few updates.

So v1 is what was originally released (I lost the original script), and without v1, this is what it is today with the script that goes with it.
I can't be bothered to understand why, etc., but in any case, the result in ps3_downloads.json was exactly the same, so at any given time, the two versions of the scripts are exactly the same, just put differently.

Feel free to rack your brains over it.
I created this script because I wanted to download everything at once, and I couldn't be bothered to do it one ID at a time (with [PySN](https://github.com/AphelionWasTaken/PySN/tree/main)), so I did it to select everything at once and download it (hence the ps3_downloads).
You can go to ps3_downloads, copy everything, and paste the download links into [Jdownloader](https://jdownloader.org/jdownloader2), which will retrieve and install everything. 


## What’s been done

- Robust parsing of the Renascene table by column headers (no fragile fixed indexes).
- Strict validation of Title IDs via regex.
- Multi-step Title ID resolution:
  1) Extract from FOLDER/TITLE when possible,
  2) Otherwise via the NFO page,
  3) Otherwise via other links found on the row.
- HTTP requests with retry/backoff and explicit User-Agent.
- ver.xml parsing (version, URL, sha1, size).
- Detailed logging: totals collected, valid IDs, 200/404/errors, updates found.
- Writes a single JSON: `ps3_updates.json` (without exact duplicates).

## Prerequisites

- Python 3.8+
- Linux (tested); should also work elsewhere if dependencies are installed.

Install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests beautifulsoup4 lxml
```

## Usage

Run the scraper:
```bash
python3 ps3-update-scraper.py
```

Main in-file parameters:
- TOTAL_PAGES: number of pages to crawl (41).
- MAX_WORKERS: request parallelism.
- REQUEST_TIMEOUT, RETRY_COUNT, BACKOFF_BASE: network tuning.
- VERIFY_SSL: set True if your CA chain is correct.

Output:
- `ps3_updates.json` at the project root.

Expected log example:
```
INFO: Total entries collected from renascene: 4100
INFO: Unique valid Title IDs to query updates for: 99 (raw valid: 0, via NFO/links: 4100; rows with links: 4100)
INFO: HTTP status counts: 200=78, ERR=21
INFO: Wrote 100 records with 103 total updates to .../ps3_updates.json
```

Notes:
- Many 404s → normal for games without patches or regional variants without a ver.xml.
- The number of download URLs < number of games: normal (not all games have a patch; some have multiple versions, others none).

## Output format

`ps3_updates.json` is a list of objects with fields from the Renascene listing and an `updates` array:
```json
{
  "TITLE": "Star_Ocean_5_Integrity_and_Faithlessness_JPN_PS3-HR",
  "FOLDER": "BLJM61325",
  "DISC_ID": "BLJM61325",
  "NFO": "https://renascene.com/ps3/?target=NFO&ID=4244",
  "RELEASED": "2016-04-28",
  "updates": [
    {
      "version": "01.02",
      "url": "https://a0.ww.np.dl.playstation.net/tpl/np/BLJM61325/...",
      "sha1sum": "…",
      "size": 123456789
    }
  ]
}
```

## Minimal JSON export (title, version, url)

To generate a file containing only the game name, version, and download URL, run: `export_min_json.py`

The `ps3_downloads.json` file will then contain only:
```json
{ "title": "Game name", "version": "01.XX", "url": "https://..." }
```

## Troubleshooting

- 0 valid IDs:
  - The HTML may have changed: check table header detection.
  - Increase REQUEST_TIMEOUT/RETRY_COUNT, change USER_AGENT.
  - Enable VERIFY_SSL if your system has a valid CA chain.
- Too many 404s:
  - Expected for many titles; check regional variants (BLES vs BLUS vs NPxx).
- Few URLs:
  - Not all titles have patches. Only ver.xml with HTTP 200 contain URLs.