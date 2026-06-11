import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        print("🚀 Launching browser...")
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Monitor requests to find CSRF token
        def handle_request(request):
            if "cometd/connect" in request.url and request.method == "POST":
                headers = request.headers
                csrf = headers.get("x-csrf-token")
                if csrf:
                    print(f"🎯 Found CSRF token in request headers: {csrf}")
                    with open(r"C:\tmp\meraki_csrf.txt", "w") as f:
                        f.write(csrf)

        page.on("request", handle_request)

        # Navigate to Meraki dashboard (Sanitized Target URL)
        test_url = "https://nXXX.meraki.com/System-Manager/n/<YOUR_NETWORK_ID>/manage/pcc/devices2?from=systems_manager+devices&search=<TARGET_DEVICE_IDENTIFIER>"
        print(f"🌐 Navigating to Meraki test URL:\n{test_url}")
        await page.goto(test_url)

        print("🔐 Log in manually in the browser window. Then press Enter here.")
        input("")

        print("⏳ Waiting for page to finish loading...")
        await page.wait_for_load_state("load")
        print("✅ Page loaded.")
        print("📍 Current URL:", page.url)

        # Extract cookies
        print("🍪 Extracting cookies...")
        cookies = await context.cookies()
        print(f"✅ Extracted {len(cookies)} cookies.")

        # Save cookies to C:\tmp
        print("💾 Saving cookies to C:\\tmp...")
        with open(r"C:\tmp\meraki_cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)

        await browser.close()
        print("🎉 Done. Cookies saved. If CSRF token was found, it’s in meraki_csrf.txt.")

asyncio.run(main())
