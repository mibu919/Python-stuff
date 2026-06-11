# Python Automation Projects

This directory contains various Python scripts built for network automation and web scraping.

## 1. Meraki CSRF Scraper (`Meraki-CSRF-Scraper.py`)
This script utilizes Playwright to automate the login flow into the Cisco Meraki dashboard. It monitors network requests in the background to automatically extract the X-CSRF-Token and active session cookies, saving them to local files for use in downstream API calls.

### Prerequisites
* Python 3.8+
* Playwright (`pip install playwright` followed by `playwright install`)

### Usage
1. Update `<YOUR_NETWORK_ID>` and `<TARGET_DEVICE_IDENTIFIER>` in the script to match your environment.
2. Run the script: `python Meraki-CSRF-Scraper.py`
3. A browser window will appear; log in manually to bypass 2FA.
4. The script automatically intercepts the token and saves it to `C:\tmp\meraki_csrf.txt`.
