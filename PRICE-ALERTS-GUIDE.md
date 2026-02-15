# 🔔 Price Alerts & Email Notifications Guide

## 🎉 What's New?

Your MarketIntel SaaS now has **SMART PRICE ALERTS WITH EMAIL NOTIFICATIONS**!

### Features Added:
- ✅ **Email Service** - Professional HTML emails with SMTP/SendGrid support
- ✅ **Alert Rules System** - Flexible price change detection
- ✅ **Database Model** - PriceAlert table with cooldown and thresholds
- ✅ **Alert API** - Full CRUD for managing alert rules
- ✅ **Automatic Checking** - Integrated with Celery for scheduled checks
- ✅ **Beautiful Email Templates** - Gradient headers, price comparisons, responsive design
- ✅ **Daily Digests** - Summary emails with top price changes

---

## 📧 Email Configuration

### Option 1: Gmail SMTP (Free, Easy Setup)

1. **Enable 2FA** on your Gmail account
2. **Create App Password**:
   - Go to: https://myaccount.google.com/apppasswords
   - Select app: "Mail"
   - Select device: "Other (Custom name)" → "MarketIntel"
   - Copy the 16-character password

3. **Add to `.env` file**:
```env
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=MarketIntel Alerts
```

### Option 2: SendGrid (Professional, High Volume)

1. **Sign up**: https://sendgrid.com/ (Free tier: 100 emails/day)
2. **Get API Key**: Settings → API Keys → Create API Key
3. **Add to `.env`**:
```env
# SendGrid Configuration
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
FROM_EMAIL=alerts@yourdomain.com
FROM_NAME=MarketIntel
```

Then update `email_service.py` to use SendGrid SDK:
```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
```

### Option 3: Other SMTP Providers

**Mailgun, Amazon SES, Postmark, etc.**
```env
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=your-mailgun-username
SMTP_PASSWORD=your-mailgun-password
```

---

## 🎯 Alert Types

### 1. **Price Drop Alert** 📉
Triggers when competitor price **decreases** by threshold

```json
{
  "product_id": 1,
  "alert_type": "price_drop",
  "threshold_pct": 5.0,
  "email": "user@example.com"
}
```

**Use Case:** "Alert me when competitor drops price by 5% so I can match it"

### 2. **Price Increase Alert** 📈
Triggers when competitor price **increases** by threshold

```json
{
  "product_id": 1,
  "alert_type": "price_increase",
  "threshold_pct": 10.0,
  "email": "user@example.com"
}
```

**Use Case:** "Alert me when competitor raises price so I can increase mine"

### 3. **Any Change Alert** 🔄
Triggers on **any** price change (up or down) exceeding threshold

```json
{
  "product_id": 1,
  "alert_type": "any_change",
  "threshold_pct": 3.0,
  "email": "user@example.com"
}
```

**Use Case:** "Alert me on any significant market movement"

### 4. **Out of Stock Alert** ❌
Triggers when competitor product becomes unavailable

```json
{
  "product_id": 1,
  "alert_type": "out_of_stock",
  "email": "user@example.com"
}
```

**Use Case:** "Alert me when competitor runs out so I can capture their customers"

---

## 🚀 Using the Alert System

### Via API (cURL Examples)

#### Create an Alert
```bash
curl -X POST http://localhost:8000/api/alerts/ \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "alert_type": "price_drop",
    "threshold_pct": 5.0,
    "email": "user@example.com",
    "cooldown_hours": 24
  }'
```

#### Get All Alerts
```bash
curl http://localhost:8000/api/alerts/
```

#### Get Alerts for Specific Product
```bash
curl http://localhost:8000/api/alerts/?product_id=1
```

#### Update Alert
```bash
curl -X PUT http://localhost:8000/api/alerts/1 \
  -H "Content-Type: application/json" \
  -d '{
    "threshold_pct": 10.0,
    "enabled": true
  }'
```

#### Delete Alert
```bash
curl -X DELETE http://localhost:8000/api/alerts/1
```

#### Toggle Alert On/Off
```bash
curl -X POST http://localhost:8000/api/alerts/1/toggle
```

#### Test Alert (Send Test Email)
```bash
curl -X POST http://localhost:8000/api/alerts/test/1
```

#### Check All Alerts Now
```bash
curl -X POST http://localhost:8000/api/alerts/check
```

---

## 📊 Email Templates

### Price Alert Email

**Features:**
- 🎨 Gradient header (purple/blue)
- 💰 Side-by-side price comparison
- 📊 Large change percentage badge
- 🔗 "View Product Details" button
- 💡 Actionable recommendation

**Preview:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  📉 PRICE ALERT                        ┃
┃  Competitor Price Change Detected      ┃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sony WH-1000XM5 Headphones

Amazon has dropped their price by -10.5%

Previous Price: $349.99  →  New Price: $314.49

[View Product Details →]

💡 This is a great opportunity to adjust your
   pricing strategy!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Daily Digest Email

**Features:**
- 📊 Three stat cards (Products, Updates, Competitors)
- 📉 Top 5 Price Drops (green)
- 📈 Top 5 Price Increases (red)
- 💡 Tip of the Day

---

## ⚙️ Alert Configuration Options

### Cooldown Period
Prevents spam - won't send duplicate alerts within this time

```json
{
  "cooldown_hours": 24  // Default: 24 hours
}
```

**Examples:**
- `6` - Alert every 6 hours max
- `24` - Once per day (default)
- `168` - Once per week

### Threshold Percentage
Minimum price change % to trigger alert

```json
{
  "threshold_pct": 5.0  // Trigger on 5% change
}
```

**Examples:**
- `1.0` - Very sensitive (1% change)
- `5.0` - Moderate (default)
- `10.0` - Only major changes
- `20.0` - Significant market shifts only

### Threshold Amount
Alternative: trigger on dollar amount change

```json
{
  "threshold_amount": 50.0  // Trigger on $50 change
}
```

**Use Case:** "Alert me if price changes by $50+ regardless of percentage"

---

## 🤖 Automatic Alert Checking

Alerts are checked automatically by Celery:

### Schedule (in `celery_app.py`):
```python
'check-price-alerts': {
    'task': 'tasks.notification_tasks.check_price_alerts',
    'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    'options': {'queue': 'notifications'}
}
```

### Manual Trigger:
```bash
# Via API
curl -X POST http://localhost:8000/api/alerts/check

# Via Scheduler UI
Visit: http://localhost:3000/scheduler
Click: "Check Price Alerts" button
```

---

## 📧 Email Delivery Best Practices

### 1. **SPF/DKIM Setup** (For Custom Domains)
If using your own domain, set up authentication:

**SPF Record:**
```
v=spf1 include:_spf.google.com ~all
```

**DKIM:** Generate in Gmail/SendGrid settings

### 2. **Avoid Spam Folder**
- Use recognizable "From" name
- Include unsubscribe link (TODO)
- Don't send too frequently
- Use proper HTML structure

### 3. **Deliverability Tips**
- Start with low volume (< 50/day)
- Warm up new sending domain gradually
- Monitor bounce rates
- Use double opt-in for users

---

## 🧪 Testing Alerts

### 1. **Test Single Alert**
```bash
# Sends test email regardless of thresholds/cooldown
curl -X POST http://localhost:8000/api/alerts/test/1
```

### 2. **Create Sample Product & Alert**
```python
# Add product
POST /products
{
  "title": "Test Product",
  "sku": "TEST-001"
}

# Add alert
POST /api/alerts/
{
  "product_id": 1,
  "alert_type": "price_drop",
  "threshold_pct": 1.0,  # Very sensitive for testing
  "email": "your-email@gmail.com",
  "cooldown_hours": 1  # Short cooldown for testing
}

# Scrape product to generate price data
POST /products/1/scrape

# Wait for next scrape or manually check
POST /api/alerts/check
```

### 3. **Check Email Logs**
```bash
# In Celery worker terminal, look for:
[2024-01-15 10:30:00] INFO: Email sent successfully to user@example.com
[2024-01-15 10:30:00] INFO: Found 3 price alerts and sent notifications
```

---

## 📊 Database Schema

### `price_alerts` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `product_id` | Integer | Foreign key to products |
| `alert_type` | String | "price_drop", "price_increase", etc. |
| `threshold_pct` | Float | Percentage threshold (e.g., 5.0) |
| `threshold_amount` | Float | Dollar amount threshold (optional) |
| `email` | String | Recipient email address |
| `enabled` | Boolean | Active/inactive |
| `cooldown_hours` | Integer | Minimum hours between alerts |
| `last_triggered_at` | DateTime | Last alert sent time |
| `created_at` | DateTime | Alert creation time |

### Example Query:
```sql
SELECT * FROM price_alerts WHERE product_id = 1 AND enabled = true;
```

---

## 🔧 Advanced Features (TODO - Future Enhancements)

### 1. **User Preferences**
```python
class User(Base):
    email_preferences = {
        'daily_digest': True,
        'instant_alerts': True,
        'weekly_summary': False
    }
```

### 2. **SMS Notifications** (via Twilio)
```python
from twilio.rest import Client
client = Client(account_sid, auth_token)
message = client.messages.create(
    body="Price Alert: Product dropped 10%",
    from_='+1234567890',
    to='+0987654321'
)
```

### 3. **Webhook Notifications**
```python
@celery_app.task
def send_webhook_alert(url, data):
    requests.post(url, json=data)
```

### 4. **Slack/Discord Integration**
```python
def send_slack_alert(webhook_url, alert_data):
    payload = {
        "text": f"🔔 Price Alert: {alert_data['product']} dropped {alert_data['change_pct']:.1f}%"
    }
    requests.post(webhook_url, json=payload)
```

### 5. **Alert Analytics**
Track alert effectiveness:
- Alert trigger rate
- Email open rate
- Click-through rate on "View Product" button
- User action taken after alert

---

## 🐛 Troubleshooting

### Email Not Sending

**Check 1: SMTP Credentials**
```bash
# Test SMTP connection
python -c "import smtplib; s=smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login('your-email@gmail.com', 'your-app-password'); print('✓ SMTP works!')"
```

**Check 2: Firewall/Network**
- Port 587 must be open
- Some ISPs block SMTP ports
- Try port 465 (SSL) instead

**Check 3: App Password**
- Must use App Password, not regular Gmail password
- 2FA must be enabled

**Check 4: Logs**
```bash
# Check Celery worker logs
tail -f celery_worker.log | grep "email"
```

### Alert Not Triggering

**Check 1: Alert Enabled?**
```bash
curl http://localhost:8000/api/alerts/1
# Check "enabled": true
```

**Check 2: Cooldown Active?**
```bash
# Check last_triggered_at
# If recent, alert is in cooldown period
```

**Check 3: Price Data Exists?**
```bash
curl http://localhost:8000/products/1/price-history
# Need at least 2 price points to detect change
```

**Check 4: Threshold Too High?**
```bash
# Lower threshold for testing
curl -X PUT http://localhost:8000/api/alerts/1 \
  -d '{"threshold_pct": 1.0}'
```

### Email Goes to Spam

**Solutions:**
1. Add sender to contacts first
2. Use SendGrid instead of Gmail SMTP
3. Set up SPF/DKIM records
4. Avoid spam trigger words ("FREE", "ACT NOW", etc.)
5. Include text version along with HTML

---

## 📚 API Documentation

Visit: **http://localhost:8000/docs**

All alert endpoints documented with:
- Request/response schemas
- Try-it-out functionality
- Example payloads
- Error codes

---

## 🎯 Real-World Use Cases

### E-commerce Store Owner
```
"Alert me when Amazon drops price by 5%+
so I can match and stay competitive"

→ Create "price_drop" alert with 5% threshold
→ Receive email within 6 hours of change
→ Adjust pricing accordingly
```

### Reseller/Arbitrage
```
"Alert me when competitor raises price by 10%+
so I can increase my margin"

→ Create "price_increase" alert with 10% threshold
→ Capitalize on competitor price hikes
```

### Supply Chain Manager
```
"Alert me when key products go out of stock
so I can reach out to customers"

→ Create "out_of_stock" alert
→ Contact customers with alternative offers
```

### Marketing Team
```
"Send me daily digest of all price changes
for weekly competitive analysis report"

→ Enable daily digest emails
→ Receive at 8 AM daily
→ Include in weekly presentations
```

---

## ✅ Setup Checklist

- [ ] Configure SMTP settings in `.env`
- [ ] Test email connection
- [ ] Create alert for test product
- [ ] Send test alert email
- [ ] Verify email received (check spam folder)
- [ ] Enable automatic alert checking in Celery
- [ ] Set up daily digest schedule
- [ ] Add SPF/DKIM records (if using custom domain)
- [ ] Monitor email delivery rates
- [ ] Create alerts for all key products

---

**Your MarketIntel SaaS now has ENTERPRISE-LEVEL price alerting!** 📧🔔

Users get instant notifications when market conditions change, enabling data-driven pricing decisions 24/7! 🚀
