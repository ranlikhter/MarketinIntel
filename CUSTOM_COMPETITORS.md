# Custom Competitor Websites Feature

## Overview

MarketIntel now supports monitoring **ANY competitor website** - not just marketplaces like Amazon or eBay!

This feature allows you to add private competitor websites and track their product prices using custom CSS selectors.

## How It Works

### 1. Add a Competitor Website

Use the API to register a new competitor:

```bash
POST http://localhost:8000/competitors
```

**Example Request:**
```json
{
  "name": "Acme Electronics",
  "base_url": "https://www.acme-electronics.com",
  "price_selector": ".product-price",
  "title_selector": "h1.product-name",
  "stock_selector": ".availability",
  "image_selector": "img.main-product-image",
  "notes": "Our main competitor in the electronics space"
}
```

### 2. Find CSS Selectors (For Beginners)

CSS selectors tell the scraper where to find product data on a webpage.

**How to find them:**

1. **Open the competitor's product page** in Chrome/Edge
2. **Right-click** on the price → Select "Inspect"
3. **Look for the HTML element** containing the price
4. **Note the class or ID**:
   - `<span class="price">$99.99</span>` → Selector: `.price`
   - `<div id="product-price">$99.99</div>` → Selector: `#product-price`

**Common Patterns:**

| Data | Common Selectors |
|------|------------------|
| Price | `.price`, `#price`, `.product-price`, `[itemprop="price"]` |
| Title | `h1`, `.product-title`, `.product-name` |
| Stock | `.availability`, `.stock-status`, `.in-stock` |
| Image | `img.product-image`, `#main-image` |

### 3. Test Your Selectors

Visit the Swagger UI at http://localhost:8000/docs to test:

1. Click **POST /competitors**
2. Enter your competitor details
3. Click "Execute"

### 4. Scrape a Product

Once a competitor is added, you can scrape any product URL from their site:

```python
# Example using the generic scraper
from backend.scrapers.generic_scraper import scrape_competitor_product

result = await scrape_competitor_product(
    url="https://acme-electronics.com/products/headphones-xyz",
    price_selector=".product-price",
    title_selector="h1.product-name"
)

print(result)
# {
#     "url": "https://acme-electronics.com/products/headphones-xyz",
#     "title": "Premium Wireless Headphones",
#     "price": 299.99,
#     "currency": "USD",
#     "in_stock": True,
#     "image_url": "https://acme-electronics.com/images/headphones.jpg"
# }
```

## API Endpoints

### List All Competitors
```
GET /competitors
GET /competitors?active_only=true
```

### Get Competitor Details
```
GET /competitors/{id}
```

### Add Competitor
```
POST /competitors
Body: { "name": "...", "base_url": "...", "price_selector": "..." }
```

### Update Competitor
```
PUT /competitors/{id}
Body: { "price_selector": ".new-selector" }
```

### Toggle Active/Inactive
```
POST /competitors/{id}/toggle
```

### Delete Competitor
```
DELETE /competitors/{id}
```

## Advanced Features

### Automatic Fallbacks

If you don't provide CSS selectors, the scraper will try common patterns automatically:

```json
{
  "name": "Simple Competitor",
  "base_url": "https://simple-store.com"
}
```

The scraper will attempt to find:
- Price using common classes: `.price`, `.product-price`
- Title from `<h1>` or meta tags
- Image from Open Graph tags

### Website Types

You can tag competitors by type:

- `"custom"` - Private competitor websites (default)
- `"amazon"` - Amazon (special handling)
- `"walmart"` - Walmart
- `"ebay"` - eBay

This helps organize your competitors and allows for specialized scrapers in the future.

### Disabling Without Deleting

To temporarily stop monitoring a competitor:

```
POST /competitors/{id}/toggle
```

This keeps all configuration but stops scraping until you re-enable it.

## Real-World Example

Let's say you sell electronics and want to monitor "TechRival.com":

### Step 1: Inspect Their Product Page

Visit: `https://techrival.com/products/sony-headphones-123`

Inspect the page and find:
- Price is in: `<span class="current-price">$249.99</span>`
- Title is in: `<h1 class="product-title">Sony WH-1000XM5</h1>`
- Stock is in: `<p class="stock">In Stock</p>`

### Step 2: Add to MarketIntel

```json
POST /competitors
{
  "name": "TechRival",
  "base_url": "https://techrival.com",
  "price_selector": ".current-price",
  "title_selector": ".product-title",
  "stock_selector": ".stock",
  "notes": "Direct competitor, similar product range"
}
```

### Step 3: Monitor Products

Now when you add a product to monitor in MarketIntel, you can scrape TechRival's equivalent product and track price changes over time!

## Troubleshooting

### "No price found"
- The CSS selector might be wrong
- Try inspecting the page again
- The price might be loaded by JavaScript (the scraper handles this with Playwright)

### "Page load timeout"
- The website might be slow or blocking scrapers
- Try again later
- Consider adding delays between requests

### "Different price format"
The scraper handles most formats automatically:
- `$99.99` ✅
- `99,99 €` ✅
- `USD 1,299.00` ✅

## Best Practices

1. **Start Simple**: Add competitors one at a time and test each
2. **Use Specific Selectors**: More specific = more reliable
3. **Add Notes**: Document why you're tracking each competitor
4. **Test Regularly**: Competitors may redesign their sites
5. **Respect Rate Limits**: Don't scrape too frequently (we add delays automatically)

## What's Next?

- **Frontend UI**: Visual interface to add/manage competitors (coming soon!)
- **Automated Monitoring**: Schedule scrapes every few hours
- **Price Alerts**: Get notified when competitor prices drop
- **Historical Charts**: View price trends over time

---

**Need Help?** Check the API docs at http://localhost:8000/docs for interactive testing!
