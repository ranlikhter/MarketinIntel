"""
AI-Powered Page Extractor

Fetches a web page, converts it to clean markdown, then uses Claude to extract
structured data from it based on a natural-language prompt.  Equivalent to
Firecrawl's /agent endpoint.

Usage:
    extractor = AIExtractor()
    result = await extractor.extract(
        url="https://example.com/product/123",
        prompt="Extract product name, price, and availability",
    )
    # result["extracted"] → {"product_name": ..., "price": ..., "availability": ...}
"""

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, Optional

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from scrapers.browser_pool import BrowserPool, rate_limiter
from scrapers.generic_scraper import GenericWebScraper

logger = logging.getLogger(__name__)

_MIN_STATIC_BODY_LEN = 500

# Maximum markdown chars sent to Claude (keeps token cost reasonable)
_MAX_MARKDOWN_CHARS = 12_000


class AIExtractor:
    """
    Uses Claude to extract structured data from any web page.

    The extraction pipeline:
      1. Fetch the page (httpx fast path, fall back to Playwright for JS sites)
      2. Convert HTML → clean markdown to reduce token usage
      3. Send markdown + user prompt to Claude
      4. Parse and return the JSON response
    """

    def __init__(self, browser_pool: Optional[BrowserPool] = None):
        self._scraper = GenericWebScraper(browser_pool=browser_pool)
        self.ua = UserAgent()

    async def extract(
        self,
        url: str,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        include_markdown: bool = False,
    ) -> Dict:
        """
        Extract structured data from a URL using a natural language prompt.

        Args:
            url:              Page to scrape.
            prompt:           Natural language description of what to extract.
                              e.g. "Extract the product name, current price,
                              was-price, and whether it's in stock."
            schema:           Optional JSON schema dict describing the expected
                              output fields.  Helps Claude produce consistent keys.
            include_markdown: If True, include the raw markdown in the response.

        Returns:
            {
                "url": str,
                "extracted": dict,          # AI-extracted fields
                "markdown": str | None,     # page markdown (if include_markdown)
                "error": str | None,
            }
        """
        result: Dict = {"url": url, "extracted": {}, "markdown": None, "error": None}

        # 1. Fetch page as markdown
        try:
            markdown = await self._fetch_as_markdown(url)
        except Exception as e:
            result["error"] = f"Page fetch failed: {e}"
            return result

        if not markdown:
            result["error"] = "Could not fetch page content"
            return result

        if include_markdown:
            result["markdown"] = markdown

        # 2. Build Claude prompt
        system_prompt = (
            "You are a precise web data extraction assistant. "
            "Given the markdown content of a web page and a user instruction, "
            "extract the requested data and return it as valid JSON only. "
            "Do not include any explanation or text outside the JSON object."
        )

        schema_hint = ""
        if schema:
            schema_hint = (
                f"\n\nReturn a JSON object matching this schema:\n```json\n"
                f"{json.dumps(schema, indent=2)}\n```"
            )

        user_message = (
            f"Extract the following from this web page:\n{prompt}{schema_hint}\n\n"
            f"---PAGE CONTENT (markdown)---\n"
            f"{markdown[:_MAX_MARKDOWN_CHARS]}"
        )

        # 3. Call Claude
        try:
            extracted = await self._call_claude(system_prompt, user_message)
            result["extracted"] = extracted
        except Exception as e:
            result["error"] = f"AI extraction failed: {e}"

        return result

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _fetch_as_markdown(self, url: str) -> str:
        """Fetch the URL and return its content as clean markdown."""
        # Respect domain rate limiting
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower().lstrip("www.")
        await rate_limiter.acquire(domain)

        # Try fast httpx path first
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": self.ua.random,
                    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=15.0,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text

            soup = BeautifulSoup(html, "html.parser")
            if len(soup.get_text(strip=True)) >= _MIN_STATIC_BODY_LEN:
                return GenericWebScraper._html_to_markdown(html)
        except Exception:
            pass

        # Fall back to Playwright for JS-rendered pages
        scrape_result = await self._scraper.scrape_product(
            url, output_format="markdown", use_javascript=True
        )
        return scrape_result.get("markdown", "") or ""

    async def _call_claude(self, system_prompt: str, user_message: str) -> Dict:
        """Send prompt to Claude and parse the JSON response."""
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")

        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        return json.loads(raw)
