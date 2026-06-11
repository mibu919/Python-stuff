"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              Meraki iPadOS Bulk Updater — API + Playwright                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT THIS SCRIPT DOES
─────────────────────
  1. Pulls all iPad device IDs from your Meraki SM network via the official API.
  2. Uses Playwright to spin up a headless browser, log into the Meraki dashboard, 
     pass through SSO/MFA, and securely capture a live session (cookies + CSRF token).
  3. Uses those captured browser credentials to send bulk POST requests to an 
     undocumented internal endpoint to force iPadOS updates across the entire fleet.

WHY THE HYBRID APPROACH?
────────────────────────
  Meraki does not expose an API endpoint for pushing OS updates. This script
  works around that platform limitation by replicating what the Meraki web 
  dashboard does internally. It authenticates as an administrator, then sends 
  the exact same internal POST requests the browser would use, completely 
  automating a process that otherwise requires thousands of manual clicks.
"""

import json
import os
import sys
import requests
import urllib.parse
import time
from pathlib import Path
from dotenv import load_dotenv

# ─── Configuration (Sanitized) ────────────────────────────────────────────────
API_KEY     = "<YOUR_MERAKI_API_KEY>"
NETWORK_ID  = "<YOUR_NETWORK_ID>"
ORG_ID      = "<YOUR_ORG_ID>"
BATCH_SIZE  = 200

POST_URL     = "https://n342.meraki.com/System-Manager/n/<YOUR_NODE>/manage/pcc/install_available_os_updates"
REFERER_URL  = "https://n342.meraki.com/System-Manager/n/<YOUR_NODE>/manage/pcc/devices2"
ELIGIBLE_URL = f"https://n342.meraki.com/api/v1/organizations/{ORG_ID}/sm/deviceCommands/installOsUpdate/eligibleDevices"
DEVICES_URL  = f"https://api.meraki.com/api/v1/networks/{NETWORK_ID}/sm/devices"

TMP = Path(r"C:\tmp")
COOKIES_PATH_PLAYWRIGHT = TMP / "meraki_cookies.json"
CSRF_PATH               = TMP / "meraki_csrf.txt"

# ─── Step 1: Fetch device IDs from official Meraki API ────────────────────────
def fetch_device_ids():
    print("\n[1/3] Fetching device IDs from Meraki API...")
    headers        = {"X-Cisco-Meraki-API-Key": API_KEY, "Content-Type": "application/json"}
    device_ids     = []
    starting_after = None

    while True:
        params   = {"startingAfter": starting_after} if starting_after else {}
        response = requests.get(DEVICES_URL, headers=headers, params=params)

        if response.status_code != 200:
            print(f"  ERROR fetching devices: {response.status_code}")
            sys.exit(1)

        page = response.json()
        if not page:
            break

        device_ids.extend(device["id"] for device in page)
        starting_after = page[-1]["id"]
        
        if len(page) < 1000:
            break

    print(f"  Done — {len(device_ids)} total device IDs.")
    return device_ids

# ─── Step 2: Auth via Playwright to capture internal CSRF & Cookies ───────────
def refresh_auth_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed.")
        sys.exit(1)

    print("\n[2/3] Opening browser for Meraki login (MFA/SSO Passthrough)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page    = context.new_page()

        page.goto(REFERER_URL)

        try:
            page.wait_for_selector('[data-testid="matching-results"]', timeout=120_000)
            print("      System Manager page loaded.")
        except Exception:
            browser.close()
            raise RuntimeError("System Manager page did not load.")

        resp = page.request.get("https://n342.meraki.com/csrf/token")
        csrf_token = resp.json().get("csrf_token")

        COOKIES_PATH_PLAYWRIGHT.write_text(json.dumps(context.cookies()))
        CSRF_PATH.write_text(csrf_token)
        print("      Cookies and CSRF token saved.")
        browser.close()

def load_auth_playwright():
    cookies       = json.loads(COOKIES_PATH_PLAYWRIGHT.read_text())
    session       = requests.Session()
    for c in cookies:
        session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))
    cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    csrf_token    = CSRF_PATH.read_text().strip()
    return session, cookie_header, csrf_token

# ─── Step 3: Fetch eligible iPadOS update IDs via undocumented API ────────────
def get_update_ids(session, device_ids):
    params = [("deviceIds[]", did) for did in device_ids[:12]]
    params.append(("networkIds[]", NETWORK_ID))

    response = session.get(ELIGIBLE_URL, params=params)
    if response.status_code in (401, 403):
        return None  # signal caller to re-auth
        
    data        = response.json()
    raw_updates = data.get("availableUpdates", "{}")
    parsed_updates = json.loads(raw_updates) if isinstance(raw_updates, str) else raw_updates

    ipad_updates = parsed_updates.get("iPadOS", [])
    update_ids   = sorted([u["id"] for u in ipad_updates if "id" in u], reverse=True)
    return update_ids

def build_headers(csrf_token, cookie_header):
    return {
        "User-Agent":       "Mozilla/5.0",
        "Accept":           "*/*",
        "Content-Type":     "application/x-www-form-urlencoded; charset=UTF-8",
        "X-CSRF-Token":     csrf_token,
        "X-Requested-With": "XMLHttpRequest",
        "Origin":           "https://n342.meraki.com",
        "Referer":          REFERER_URL,
        "Cookie":           cookie_header,
    }

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    device_ids = fetch_device_ids()

    if not COOKIES_PATH_PLAYWRIGHT.exists() or not CSRF_PATH.exists():
        refresh_auth_playwright()
    session, cookie_header, csrf_token = load_auth_playwright()

    print("\n[3/3] Pushing updates via undocumented POST endpoint...")
    update_ids = get_update_ids(session, device_ids)

    if not update_ids:
        print("No iPadOS updates available. Nothing to do.")
        sys.exit(0)

    # Chunk into manageable batches to prevent timeout
    batches  = [device_ids[i:i + BATCH_SIZE] for i in range(0, len(device_ids), BATCH_SIZE)]
    success  = 0

    for i, batch in enumerate(batches, start=1):
        for update_id in update_ids:
            payload = [("ids[]", did) for did in batch]
            payload.append(("opts[iPadOS][osVersion]",    update_id))
            payload.append(("opts[iPadOS][installAction]", "Default"))

            resp = session.post(POST_URL, headers=build_headers(csrf_token, cookie_header),
                                data=urllib.parse.urlencode(payload))

            if resp.status_code == 200:
                success += 1
            time.sleep(1)

    print(f"\nDone. {success} batch(es) succeeded.")

if __name__ == "__main__":
    main()
