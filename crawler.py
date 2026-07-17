import asyncio
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from config import config
from utils import info, warning
from urllib.parse import urljoin, urlparse
from pathlib import Path

_JS_EVENT_TRACKER_SCRIPT = """
(() => {
    if (window.__eventTrackerInstalled) return;
    window.__eventTrackerInstalled = true;
    window.__capturedEvents = [];

    const originalAdd = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function (type, listener, options) {
        try {
            let tag = "unknown";
            if (this === window) tag = "window";
            else if (this === document) tag = "document";
            else if (this && this.tagName) tag = this.tagName.toLowerCase();

            window.__capturedEvents.push({
                element: tag,
                id: (this && this.id) || "",
                class: (this && typeof this.className === "string") ? this.className : "",
                event: type,
            });
        } catch (e) {}
        return originalAdd.call(this, type, listener, options);
    };
})();
"""

_NOISY_RESOURCE_TYPES = {
    "stylesheet", "image", "media", "font", "other",
    "manifest", "texttrack", "websocket", "eventsource",
    "preflight", "signedexchange", "ping",
}

_INVALID_LINK_PREFIXES = {
    "javascript:", "mailto:", "tel:", "sms:", "data:", "#",
}


class WebsiteCrawler:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.network_logs = []
        self.console_logs = []

    async def start_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=config.HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.context = await self.browser.new_context(
            viewport=config.VIEWPORT,
            user_agent=config.USER_AGENT,
        )
        await self.context.add_init_script(_JS_EVENT_TRACKER_SCRIPT)
        self.page = await self.context.new_page()
        self.page.on("request", self._on_request)
        self.page.on("console", self._on_console)

    async def close_browser(self):
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass

    def _on_request(self, request):
        resource_type = request.resource_type
        if resource_type in _NOISY_RESOURCE_TYPES:
            return
        self.network_logs.append({
            "url": request.url,
            "method": request.method,
            "resource_type": resource_type,
        })

    def _on_console(self, msg):
        self.console_logs.append({"type": msg.type, "text": msg.text})

    async def crawl(self, url):
        await self.start_browser()
        try:
            info(f"Crawling {url}")
            data = await self._crawl_page(url)
            data["network"] = self.network_logs
            data["console_logs"] = self.console_logs
            data["cookies"] = await self._collect_cookies()
            data["local_storage"] = await self._collect_local_storage()
            data["session_storage"] = await self._collect_session_storage()
            data["statistics"] = {
                "forms": len(data["forms"]),
                "inputs": len(data["inputs"]),
                "selects": len(data["selects"]),
                "buttons": len(data["buttons"]),
                "links": len(data["links"]),
                "tables": len(data["tables"]),
                "images": len(data["images"]),
                "network_requests": len(data["network"]),
                "console_logs": len(data["console_logs"]),
                "js_events": len(data["js_events"].get("dynamic_listeners", [])) + len(data["js_events"].get("inline_handlers", [])),
            }
            return data
        finally:
            await self.close_browser()

    async def _goto_with_retry(self, url, attempts=3):
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=config.PAGE_TIMEOUT)
                return
            except Exception as e:
                last_error = e
                warning(f"goto() lần {attempt}/{attempts} lỗi: {e}")
                if attempt < attempts:
                    await asyncio.sleep(2 * attempt)
        raise RuntimeError(f"Không thể tải trang '{url}' sau {attempts} lần thử.")

    async def _crawl_page(self, url):
        await self._goto_with_retry(url)
        try:
            await self.page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        await self.page.wait_for_timeout(config.WAIT_TIME)
        await self._wait_for_spa_ready()
        await self._scroll_for_lazy_load()
        
        html = await self.page.content()
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        clean_text = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True))

        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "html": str(soup),
            "clean_text": clean_text,
            "forms": await self._collect_forms(soup),
            "inputs": await self._collect_inputs(soup),
            "selects": await self._collect_selects(soup),
            "buttons": await self._collect_buttons(soup),
            "links": await self._collect_links(soup),
            "tables": await self._collect_tables(soup),
            "images": await self._collect_images(soup),
            "metadata": await self._collect_metadata(soup),
            "accessibility_tree": await self._collect_accessibility_tree(),
            "js_events": await self._collect_js_events(),
        }

    async def _wait_for_spa_ready(self):
        try:
            await self.page.wait_for_function(
                """() => {
                    if (document.readyState !== "complete") return false;
                    const loading = document.querySelectorAll('[aria-busy="true"], [data-loading]');
                    return loading.length === 0;
                }""",
                timeout=5000,
            )
        except Exception:
            pass

    async def _scroll_for_lazy_load(self):
        try:
            for _ in range(10):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.page.wait_for_timeout(500)
            await self.page.evaluate("window.scrollTo(0, 0)")
        except Exception:
            pass

    async def _collect_forms(self, soup):
        forms = []
        for form in soup.find_all('form'):
            forms.append({
                "index": len(forms) + 1,
                "id": form.get('id', ''),
                "action": form.get('action', ''),
                "method": form.get('method', 'GET').upper(),
                "input_count": len(form.find_all("input")),
                "button_count": len(form.find_all(["input", "button"])),
                "select_count": len(form.find_all('select')),
            })
        return forms

    async def _collect_inputs(self, soup):
        results = []
        for input_tag in soup.find_all('input'):
            results.append({
                "index": len(results) + 1,
                "type": input_tag.get('type', 'text'),
                "id": input_tag.get('id', ''),
                "name": input_tag.get('name', ''),
                "placeholder": input_tag.get('placeholder', ''),
                "required": input_tag.has_attr('required'),
            })
        return results

    async def _collect_selects(self, soup):
        results = []
        for select_tag in soup.find_all('select'):
            options = [option.text.strip() for option in select_tag.find_all('option')]
            results.append({
                "index": len(results) + 1,
                "id": select_tag.get('id', ''),
                "name": select_tag.get('name', ''),
                "options_count": len(options),
                "options": options,
            })
        return results

    async def _collect_buttons(self, soup):
        results = []
        for button_tag in soup.find_all('button'):
            results.append({
                "index": len(results) + 1,
                "text": button_tag.text.strip(),
                "id": button_tag.get('id', ''),
                "type": button_tag.get('type', 'button'),
            })
        return results

    async def _collect_links(self, soup):
        results = []
        for link_tag in soup.find_all('a'):
            href = link_tag.get('href', '')
            if any(href.startswith(prefix) for prefix in _INVALID_LINK_PREFIXES):
                continue
            results.append({
                "index": len(results) + 1,
                "text": link_tag.text.strip(),
                "href": href,
            })
        return results

    async def _collect_tables(self, soup):
        tables = []
        for table_tag in soup.find_all('table'):
            headers = [th.text.strip() for th in table_tag.find_all('th')]
            rows = []
            for tr_tag in table_tag.find_all('tr'):
                row_data = [td.text.strip() for td in tr_tag.find_all('td')]
                if row_data:
                    rows.append(row_data)
            tables.append({
                "index": len(tables) + 1,
                "headers": headers,
                "rows": rows,
                "row_count": len(rows),
                "column_count": len(headers),
            })
        return tables

    async def _collect_images(self, soup):
        images = []
        for img_tag in soup.find_all('img'):
            images.append({
                "index": len(images) + 1,
                "src": img_tag.get('src', ''),
                "alt": img_tag.get('alt', ''),
            })
        return images

    async def _collect_metadata(self, soup):
        metadata = {"title": await self.page.title()}
        for key, selector in [
            ("description", 'meta[name="description"]'),
            ("keywords", 'meta[name="keywords"]'),
        ]:
            try:
                metadata[key] = await self.page.locator(selector).get_attribute("content")
            except Exception:
                metadata[key] = ""
        return metadata

    async def _collect_accessibility_tree(self):
        if not config.CAPTURE_ACCESSIBILITY_TREE:
            return {}
        try:
            snapshot = await self.page.accessibility.snapshot()
            return snapshot if snapshot else {}
        except Exception:
            return {}

    async def _collect_js_events(self):
        try:
            captured = await self.page.evaluate("window.__capturedEvents || []")
        except Exception:
            captured = []
        return {"dynamic_listeners": captured, "inline_handlers": []}

    async def _collect_cookies(self):
        cookies = await self.context.cookies()
        return [{"name": c.get("name"), "domain": c.get("domain")} for c in cookies]

    async def _collect_local_storage(self):
        return await self.page.evaluate(
            "(() => { let data = {}; for (let i = 0; i < localStorage.length; i++) { let key = localStorage.key(i); data[key] = localStorage.getItem(key); } return data; })()"
        )

    async def _collect_session_storage(self):
        return await self.page.evaluate(
            "(() => { let data = {}; for (let i = 0; i < sessionStorage.length; i++) { let key = sessionStorage.key(i); data[key] = sessionStorage.getItem(key); } return data; })()"
        )


async def run(url):
    crawler = WebsiteCrawler()
    return await crawler.crawl(url)


def crawl_sync(url):
    """Wrapper đồng bộ để gọi từ app.py."""
    return asyncio.run(run(url))
