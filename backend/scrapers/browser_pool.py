"""
Shared scraper infrastructure for optimal performance.

  BrowserPool        — persistent Chromium instances; eliminates the 2-3 s
                       browser-startup cost on every scrape call.
  CircuitBreaker     — stops hammering domains that are actively blocking us.
  DomainRateLimiter  — throttles requests per domain to avoid IP bans.
  ResponseCache      — short-TTL in-memory cache; skips duplicate scrapes.
"""

import asyncio
import contextlib
import itertools
import logging
import time
from typing import Dict, List, Optional

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


# ── Browser Pool ──────────────────────────────────────────────────────────────

class BrowserPool:
    """
    Maintains a pool of persistent Chromium browser instances.

    Browsers are launched once and reused across scrape calls.  Each call
    gets its own browser *context* (fresh cookies/state) so sessions are
    fully isolated, but the expensive process-launch step is paid only once.

    Usage (within an async function):
        pool = BrowserPool(pool_size=2)
        async with pool.acquire_page(user_agent="...") as page:
            await page.goto(url)
        await pool.close()   # call once at shutdown
    """

    _LAUNCH_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-web-security",
    ]

    def __init__(self, pool_size: int = 2):
        self.pool_size = pool_size
        self._playwright = None
        self._browsers: List = []
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._lock = asyncio.Lock()
        self._started = False
        self._browser_cycle = None   # itertools.cycle — set in start()

    async def start(self):
        """Launch all browsers. Called automatically on first acquire_page()."""
        async with self._lock:
            if self._started:
                return
            self._playwright = await async_playwright().start()
            self._semaphore = asyncio.Semaphore(self.pool_size)
            for _ in range(self.pool_size):
                browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=self._LAUNCH_ARGS,
                )
                self._browsers.append(browser)
            self._browser_cycle = itertools.cycle(self._browsers)
            self._started = True
            logger.info("BrowserPool started with %d browser(s)", self.pool_size)

    @contextlib.asynccontextmanager
    async def acquire_page(
        self,
        user_agent: Optional[str] = None,
        viewport: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
    ):
        """
        Async context manager that yields a ready Playwright page.

        The underlying browser context (and page) is closed after the block;
        the browser process itself remains alive for the next caller.
        """
        if not self._started:
            await self.start()

        viewport = viewport or {"width": 1920, "height": 1080}
        async with self._semaphore:
            browser = next(self._browser_cycle)
            ctx_kwargs: dict = {"viewport": viewport}
            if user_agent:
                ctx_kwargs["user_agent"] = user_agent
            context = await browser.new_context(**ctx_kwargs)
            if extra_headers:
                await context.set_extra_http_headers(extra_headers)
            page = await context.new_page()
            try:
                yield page
            finally:
                await context.close()

    async def close(self):
        """Shut down all browsers and the Playwright instance."""
        for browser in self._browsers:
            try:
                await browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._browsers.clear()
        self._started = False
        logger.info("BrowserPool closed")


# ── Circuit Breaker ───────────────────────────────────────────────────────────

class CircuitBreaker:
    """
    Prevents wasting requests on domains that are actively blocking us.

    After `failure_threshold` consecutive failures the circuit "opens" and
    all further requests for that domain are refused immediately.  The circuit
    automatically "closes" (allows requests again) after `recovery_timeout`
    seconds.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures: Dict[str, int] = {}
        self._open_until: Dict[str, float] = {}

    def is_open(self, domain: str) -> bool:
        """Return True if the circuit is open (domain is currently blocked)."""
        until = self._open_until.get(domain, 0.0)
        if time.time() < until:
            return True
        # Recovery window has passed — reset counters
        if domain in self._open_until:
            del self._open_until[domain]
            self._failures[domain] = 0
        return False

    def record_failure(self, domain: str):
        self._failures[domain] = self._failures.get(domain, 0) + 1
        if self._failures[domain] >= self.failure_threshold:
            self._open_until[domain] = time.time() + self.recovery_timeout
            self._failures[domain] = 0
            logger.warning(
                "CircuitBreaker: %s opened for %ds after %d failures",
                domain, self.recovery_timeout, self.failure_threshold,
            )

    def record_success(self, domain: str):
        self._failures.pop(domain, None)
        self._open_until.pop(domain, None)

    def seconds_until_reset(self, domain: str) -> float:
        return max(0.0, self._open_until.get(domain, 0.0) - time.time())


# ── Domain Rate Limiter ───────────────────────────────────────────────────────

class DomainRateLimiter:
    """
    Enforces a minimum interval between requests to the same domain.

    All concurrent workers share the same limiter instance, so they
    naturally stagger their requests rather than stampeding a single host.
    """

    def __init__(self, requests_per_minute: int = 20):
        self.min_interval = 60.0 / requests_per_minute
        self._last_request: Dict[str, float] = {}
        self._domain_locks: Dict[str, asyncio.Lock] = {}
        self._meta_lock = asyncio.Lock()

    async def _get_domain_lock(self, domain: str) -> asyncio.Lock:
        async with self._meta_lock:
            if domain not in self._domain_locks:
                self._domain_locks[domain] = asyncio.Lock()
            return self._domain_locks[domain]

    async def acquire(self, domain: str):
        """Wait if necessary, then register the current request for `domain`."""
        lock = await self._get_domain_lock(domain)
        async with lock:
            elapsed = time.time() - self._last_request.get(domain, 0.0)
            wait = self.min_interval - elapsed
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request[domain] = time.time()


# ── Response Cache ────────────────────────────────────────────────────────────

class ResponseCache:
    """
    Short-TTL in-memory cache for scrape results.

    Prevents the same URL from being fetched twice within the TTL window,
    which can happen when multiple Celery tasks are triggered for the same
    product in quick succession.
    """

    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._store: Dict[str, tuple] = {}   # url -> (result, timestamp)
        self._last_cleanup: float = 0.0

    def get(self, url: str) -> Optional[dict]:
        entry = self._store.get(url)
        if entry:
            result, ts = entry
            if time.time() - ts < self.ttl:
                return result
            del self._store[url]
        return None

    def set(self, url: str, result: dict):
        now = time.time()
        self._store[url] = (result, now)
        # Periodic GC: clear stale entries at most once per TTL period so the
        # dict doesn't grow without bound over hours of operation.
        if now - self._last_cleanup > self.ttl:
            self.clear_expired()
            self._last_cleanup = now

    def invalidate(self, url: str):
        self._store.pop(url, None)

    def clear_expired(self):
        now = time.time()
        expired = [u for u, (_, ts) in self._store.items() if now - ts >= self.ttl]
        for u in expired:
            del self._store[u]


# ── Shared module-level singletons ────────────────────────────────────────────
# These are intentionally NOT browser pools (pools are event-loop-scoped).
# Circuit breaker, rate limiter, and response cache are pure-Python and safe
# to share across the process lifetime.

circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=300)
rate_limiter = DomainRateLimiter(requests_per_minute=20)
# 3600 s (1 h) TTL: if the same URL is queued again within an hour we return
# the cached scrape instead of hitting the live page.  5 min was too short —
# multiple Celery workers triggered on the same product would both hit Amazon.
response_cache = ResponseCache(ttl_seconds=3600)
