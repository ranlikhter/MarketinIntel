# 🔌 Product Integrations Guide

Import products from XML files, WooCommerce, or Shopify stores instantly!

---

## 🚀 Overview

MarketIntel now supports **3 powerful ways** to import your products:

1. **XML File Upload** - Upload product feeds (Google Shopping, WooCommerce XML, custom formats)
2. **WooCommerce Integration** - Direct API connection to your WooCommerce store
3. **Shopify Integration** - Connect to your Shopify store via Admin API

---

## 📋 Features

✅ **Fast Bulk Import** - Import 100s of products in seconds
✅ **Duplicate Detection** - Automatically skips existing products
✅ **Auto-format Detection** - Recognizes XML format automatically
✅ **Secure API Connections** - Encrypted credential storage
✅ **Import Progress Tracking** - Real-time import status
✅ **Error Handling** - Clear error messages and partial imports

---

## 1️⃣ XML File Import

### Supported Formats

- **Google Shopping Feed** - Standard product XML feeds
- **WooCommerce Export** - Native WooCommerce XML exports
- **Custom XML** - Flexible parser supports most XML structures

### How to Import

1. Navigate to **Integrations** page
2. Click "Import from XML"
3. Upload your XML file
4. Select format (or use auto-detect)
5. Click "Import Products"

### XML Format Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<products>
    <product>
        <title>Sony WH-1000XM5 Headphones</title>
        <brand>Sony</brand>
        <sku>WH1000XM5</sku>
        <price>399.99</price>
        <image>https://example.com/image.jpg</image>
        <description>Premium noise-canceling headphones</description>
        <category>Electronics</category>
    </product>
</products>
```

### Supported Fields

| Field       | Required | Description                |
|-------------|----------|----------------------------|
| title       | ✅ Yes    | Product name               |
| brand       | ❌ No     | Manufacturer/brand         |
| sku         | ❌ No     | Product SKU/ID             |
| price       | ❌ No     | Product price              |
| image       | ❌ No     | Image URL                  |
| description | ❌ No     | Product description        |
| category    | ❌ No     | Product category           |

---

## 2️⃣ WooCommerce Integration

### Prerequisites

1. **WooCommerce Store** (any version)
2. **REST API Enabled** (enabled by default)
3. **API Credentials** (Consumer Key + Secret)

### Getting API Credentials

1. Login to your WordPress admin
2. Go to **WooCommerce → Settings → Advanced → REST API**
3. Click **"Add Key"**
4. Choose:
   - Description: "MarketIntel Integration"
   - User: Select admin user
   - Permissions: **Read**
5. Click **"Generate API Key"**
6. **Save** Consumer Key and Consumer Secret

### How to Import

1. Navigate to **Integrations** page
2. Click "Connect WooCommerce"
3. Enter credentials:
   - **Store URL**: https://yourstore.com
   - **Consumer Key**: ck_xxxxxxxxxxxxx
   - **Consumer Secret**: cs_xxxxxxxxxxxxx
   - **Import Limit**: 100 (adjust as needed)
4. Click "Import Products"

### API Endpoints Used

- `GET /wp-json/wc/v3/products` - Fetch products
- `GET /wp-json/wc/v3/products/categories` - Fetch categories

### Imported Fields

| WooCommerce Field | MarketIntel Field |
|-------------------|-------------------|
| name              | title             |
| sku               | sku               |
| images[0].src     | image_url         |
| description       | description       |
| price             | price             |
| permalink         | link              |
| brands/attributes | brand             |
| categories        | category          |

---

## 3️⃣ Shopify Integration

### Prerequisites

1. **Shopify Store** (any plan)
2. **Admin API Access**
3. **Access Token**

### Getting Admin API Access Token

#### Option 1: Custom App (Recommended)

1. Login to Shopify admin
2. Go to **Settings → Apps and sales channels**
3. Click **"Develop apps"**
4. Click **"Create an app"**
5. Name: "MarketIntel Integration"
6. Click **"Configure Admin API scopes"**
7. Select: **read_products**
8. Click **"Install app"**
9. Click **"Reveal token once"**
10. **Copy** the Admin API access token

#### Option 2: Private App (Legacy)

1. Go to **Apps → Manage private apps**
2. Click **"Create new private app"**
3. Enable **"Read access"** for Products
4. **Save** and copy the API password

### How to Import

1. Navigate to **Integrations** page
2. Click "Connect Shopify"
3. Enter credentials:
   - **Shop URL**: your-store.myshopify.com
   - **Access Token**: shpat_xxxxxxxxxxxxx
   - **Import Limit**: 100 (adjust as needed)
4. Click "Import Products"

### API Endpoints Used

- `GET /admin/api/2024-01/products.json` - Fetch products
- `GET /admin/api/2024-01/custom_collections.json` - Fetch collections

### Imported Fields

| Shopify Field      | MarketIntel Field |
|--------------------|-------------------|
| title              | title             |
| vendor             | brand             |
| variants[0].sku    | sku               |
| images[0].src      | image_url         |
| body_html          | description       |
| variants[0].price  | price             |
| handle             | link              |
| product_type       | category          |

---

## 🔧 Technical Details

### Backend Architecture

```
backend/
├── integrations/
│   ├── xml_parser.py          # XML file parser
│   ├── woocommerce_integration.py  # WooCommerce API client
│   └── shopify_integration.py      # Shopify API client
└── api/routes/
    └── integrations.py         # Integration API endpoints
```

### API Endpoints

#### POST `/api/integrations/import/xml`
Upload and import XML file
- **Body**: multipart/form-data
- **Fields**: file (XML), format_type (string)

#### POST `/api/integrations/import/woocommerce`
Import from WooCommerce
- **Body**: JSON
```json
{
  "store_url": "https://yourstore.com",
  "consumer_key": "ck_xxxxx",
  "consumer_secret": "cs_xxxxx",
  "import_limit": 100
}
```

#### POST `/api/integrations/import/shopify`
Import from Shopify
- **Body**: JSON
```json
{
  "shop_url": "your-store.myshopify.com",
  "access_token": "shpat_xxxxx",
  "import_limit": 100
}
```

#### POST `/api/integrations/test/woocommerce`
Test WooCommerce connection

#### POST `/api/integrations/test/shopify`
Test Shopify connection

#### GET `/api/integrations/sample/xml`
Get sample XML format

### Response Format

```json
{
  "success": true,
  "products_imported": 45,
  "products_skipped": 3,
  "errors": []
}
```

---

## 🎯 Best Practices

### XML Import

✅ **DO:**
- Use UTF-8 encoding
- Include required fields (title minimum)
- Keep file size under 10MB
- Validate XML structure before upload

❌ **DON'T:**
- Use non-standard characters without encoding
- Upload files larger than 10MB
- Include sensitive data in XML

### WooCommerce

✅ **DO:**
- Use Read-only API keys
- Test connection before bulk import
- Import in batches (100-500 products)
- Keep credentials secure

❌ **DON'T:**
- Share API credentials
- Use Write permissions (not needed)
- Import all products at once (>1000)

### Shopify

✅ **DO:**
- Use scoped access tokens
- Limit permissions to read_products only
- Test connection first
- Monitor API rate limits

❌ **DON'T:**
- Use unnecessary permissions
- Share access tokens
- Exceed API rate limits (2 requests/second)

---

## 🐛 Troubleshooting

### XML Import Issues

**Problem**: "Failed to parse XML"
- **Solution**: Validate XML structure, ensure UTF-8 encoding

**Problem**: "No products found"
- **Solution**: Check XML format, try different format type

**Problem**: "All products skipped"
- **Solution**: Products already exist (check by SKU/title)

### WooCommerce Issues

**Problem**: "Connection failed"
- **Solution**:
  - Check store URL (must include https://)
  - Verify API credentials
  - Ensure REST API is enabled
  - Check firewall/security plugins

**Problem**: "401 Unauthorized"
- **Solution**:
  - Regenerate API keys
  - Check key permissions (needs Read)
  - Verify user has admin role

**Problem**: "SSL Certificate Error"
- **Solution**:
  - Ensure store has valid SSL certificate
  - Update WooCommerce to latest version

### Shopify Issues

**Problem**: "Connection failed"
- **Solution**:
  - Verify shop URL format (.myshopify.com)
  - Check access token
  - Ensure app has read_products scope

**Problem**: "403 Forbidden"
- **Solution**:
  - Reinstall app with correct permissions
  - Generate new access token

**Problem**: "Rate limit exceeded"
- **Solution**:
  - Reduce import limit
  - Wait 1 minute before retrying

---

## 📊 Performance

| Method      | Speed        | Products/Second | Recommended Batch Size |
|-------------|--------------|-----------------|------------------------|
| XML         | ⚡ Very Fast | 50-100          | 500                    |
| WooCommerce | 🚀 Fast      | 20-30           | 100-200                |
| Shopify     | 🏃 Moderate  | 10-20           | 100                    |

---

## 🔐 Security

### Data Privacy

- ✅ API credentials are **never stored** permanently
- ✅ All API requests use **HTTPS encryption**
- ✅ Credentials are **not logged**
- ✅ Import process runs **server-side**

### API Permissions

**Minimum Required:**

- **WooCommerce**: `read` only
- **Shopify**: `read_products` only

**Never Use:**
- ❌ Write permissions
- ❌ Delete permissions
- ❌ Admin/full access

---

## 💡 Tips & Tricks

### Speed Up Imports

1. **Use XML for large catalogs** (500+ products)
2. **Import in batches** during off-peak hours
3. **Filter by category** for WooCommerce/Shopify
4. **Use import limits** to avoid timeouts

### Avoid Duplicates

1. **Use consistent SKUs** across platforms
2. **Unique product titles** help detection
3. **Review skipped products** in import results

### Organize Products

1. **Import by category** for better organization
2. **Tag imported products** with source
3. **Review and clean** after import

---

## 🚀 What's Next?

### Coming Soon

- 🔄 **Scheduled Imports** - Auto-sync daily/weekly
- 📊 **Import History** - Track all past imports
- 🔔 **Import Notifications** - Email alerts on completion
- 🎯 **Advanced Filtering** - Import specific categories/brands
- 🌐 **More Platforms** - Magento, BigCommerce, etc.

---

## 📚 Resources

### Documentation

- [WooCommerce REST API Docs](https://woocommerce.github.io/woocommerce-rest-api-docs/)
- [Shopify Admin API Docs](https://shopify.dev/docs/api/admin-rest)
- [Google Shopping Feed Spec](https://support.google.com/merchants/answer/7052112)

### Video Tutorials

- 🎥 XML Import Tutorial (coming soon)
- 🎥 WooCommerce Setup Guide (coming soon)
- 🎥 Shopify Integration Guide (coming soon)

---

## 🆘 Need Help?

**Got questions?** Open an issue on GitHub or contact support!

**Found a bug?** Please report it with:
- Import type (XML/WooCommerce/Shopify)
- Error message
- Steps to reproduce

---

**Happy Importing!** 🎉

Your products are just a few clicks away from competitor price monitoring!
