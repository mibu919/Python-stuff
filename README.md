# 🐍 Python Automation & Web Scraping

This directory contains advanced Python scripts designed to automate complex, bulk administration tasks by interacting with vendor APIs and bypassing platform limitations via headless browser automation.

### 📜 Included Scripts

#### 1. `Meraki-iPadOS-Bulk-Updater.py` (Hybrid API & Playwright)
**Purpose:** Forces iPadOS updates across an entire managed fleet.
- **Why it's advanced:** Meraki's front-facing API natively lacks the ability to push OS updates to iPads. This script solves that by using `playwright.async_api` to spin up a headless Chromium session, authenticate through Meraki's SSO/MFA, and securely extract internal session cookies and the `X-CSRF-Token`. It then blends these captured credentials with the `requests` library to send bulk POST requests directly to Meraki's internal, undocumented dashboard endpoints, completely automating a process that would otherwise require thousands of manual clicks.

#### 2. `Newline-Device-Toolkit.py` (Undocumented API Automation)
**Purpose:** Mass-management of Newline interactive panels.
- **Why it's advanced:** The vendor provided no bulk-action GUI or public documentation for firmware updates. This script reverse-engineers the vendor's API endpoints. It constructs deeply nested JSON payloads, manages pagination, and concurrently pushes batch maintenance commands (Firmware Updates, Restarts, Device Locks) to groups of 100 panels at a time, proving advanced MDM capability even on closed systems.

#### 3. `Meraki-CSRF-Scraper.py` (Request Interception)
**Purpose:** A focused Playwright scraper used to actively intercept web traffic.
- **Why it's advanced:** Instead of just scraping HTML, it implements a custom request interceptor within Playwright. It actively monitors for specific `POST` requests in the background, gracefully extracts internal CSRF tokens directly from the request headers, and dumps the active session cookies into a local JSON file for downstream automation tools to consume.

### ⚙️ Prerequisites
To run these scripts, you will need to install the required Python libraries:
```bash
pip install requests pandas playwright python-dotenv
playwright install chromium
```
