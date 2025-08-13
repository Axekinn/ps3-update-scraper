# ps3-update-scraper
Scraper that: - Fetches the list of PS3 releases from Renascene (41 pages). - Resolves valid PS3 Title IDs (BLES/BLUS/BCES/BCUS/BLJM/BLJS/NPxx) from columns, NFO pages, and row links. - Queries Sony’s endpoint for each Title ID and parses ver.xml files. - Produces a consolidated JSON with available updates.
