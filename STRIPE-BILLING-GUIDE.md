# Stripe Billing Integration Guide

> **Updated 2026-02-22** — Fully implemented and live. Manage billing from Settings → Billing tab in the app.

## Overview
Complete guide to setting up Stripe billing for MarketIntel SaaS subscriptions.

## Features Implemented
- ✅ Stripe Checkout for subscription upgrades
- ✅ Customer Portal for subscription management
- ✅ Webhook handling for subscription events
- ✅ Usage limits enforcement based on subscription tier
- ✅ Automatic tier upgrades/downgrades
- ✅ Frontend pricing page with billing toggle

---

## Setup Instructions

### 1. Create Stripe Account
1. Go to https://stripe.com and sign up
2. Complete your account setup
3. Switch to Test Mode (toggle in top right)

### 2. Get API Keys
1. Go to Developers → API Keys
2. Copy your **Secret Key** (starts with `sk_test_`)
3. Copy your **Publishable Key** (starts with `pk_test_`)
4. Add to `.env`:
```env
STRIPE_SECRET_KEY=sk_test_your_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
```

### 3. Create Products and Prices

#### Create Products
1. Go to Products in Stripe Dashboard
2. Create 3 products:
   - **MarketIntel Pro**
   - **MarketIntel Business**
   - **MarketIntel Enterprise**

#### Create Prices for Each Product

**Pro Plan:**
- Monthly: $49/month
  - Copy the Price ID (e.g., `price_1ABC123...`)
- Yearly: $490/year
  - Copy the Price ID

**Business Plan:**
- Monthly: $149/month
- Yearly: $1490/year

**Enterprise Plan:**
- Monthly: $499/month
- Yearly: $4990/year

#### Add Price IDs to `.env`
```env
STRIPE_PRICE_PRO_MONTHLY=price_xxx
STRIPE_PRICE_PRO_YEARLY=price_xxx
STRIPE_PRICE_BUSINESS_MONTHLY=price_xxx
STRIPE_PRICE_BUSINESS_YEARLY=price_xxx
STRIPE_PRICE_ENTERPRISE_MONTHLY=price_xxx
STRIPE_PRICE_ENTERPRISE_YEARLY=price_xxx
```

### 4. Setup Webhook Endpoint

#### Create Webhook in Stripe
1. Go to Developers → Webhooks
2. Click "Add endpoint"
3. Enter endpoint URL:
   ```
   http://localhost:8000/api/billing/webhook
   ```
   (For production, use your domain)

4. Select events to listen to:
   - ✅ `checkout.session.completed`
   - ✅ `customer.subscription.created`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `invoice.payment_succeeded`
   - ✅ `invoice.payment_failed`

5. Copy the **Webhook Signing Secret** (starts with `whsec_`)

6. Add to `.env`:
```env
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### 5. Test Webhook Locally (Development)

Use Stripe CLI to forward webhooks to localhost:

```bash
# Install Stripe CLI
# https://stripe.com/docs/stripe-cli

# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/api/billing/webhook

# This will give you a webhook signing secret starting with whsec_
# Copy it to your .env file
```

---

## Testing the Integration

### Test Subscription Flow

1. **Start the backend:**
```bash
cd backend
uvicorn api.main:app --reload
```

2. **Start the frontend:**
```bash
cd frontend
npm run dev
```

3. **Test signup:**
   - Go to http://localhost:3000/auth/signup
   - Create a new account (FREE tier)
   - You should be logged in automatically

4. **Test subscription upgrade:**
   - Go to http://localhost:3000/pricing
   - Click "Start Free Trial" on Pro plan
   - You'll be redirected to Stripe Checkout
   - Use test card: `4242 4242 4242 4242`
   - Any future expiry date (e.g., 12/25)
   - Any 3-digit CVC
   - Complete the checkout

5. **Verify subscription:**
   - You should be redirected to dashboard
   - Check your user in the database - tier should be PRO
   - Limits should be updated:
     - products_limit: 50
     - matches_limit: 100
     - alerts_limit: 10

### Test Stripe Customer Portal

1. **Access billing settings:**
   - Make API call to create portal session:
```javascript
fetch('http://localhost:8000/api/billing/create-portal-session', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    return_url: 'http://localhost:3000/settings'
  })
})
```

2. **In the portal you can:**
   - Update payment method
   - Cancel subscription
   - View invoices
   - Update billing information

### Test Webhook Events

With Stripe CLI running:

1. **Test subscription created:**
```bash
stripe trigger customer.subscription.created
```

2. **Test payment succeeded:**
```bash
stripe trigger invoice.payment_succeeded
```

3. **Check your terminal** - you should see webhook events being received

---

## Subscription Tiers & Limits

| Tier | Monthly | Yearly | Products | Matches | Alerts | API Calls |
|------|---------|--------|----------|---------|--------|-----------|
| FREE | $0 | $0 | 5 | 10 | 1 | 0 |
| PRO | $49 | $490 | 50 | 100 | 10 | 1,000/mo |
| BUSINESS | $149 | $1,490 | 200 | 500 | 50 | 10,000/mo |
| ENTERPRISE | $499 | $4,990 | Unlimited | Unlimited | Unlimited | Unlimited |

**Yearly savings: 17% off** (equivalent to 2 months free)

---

## API Endpoints

### Create Checkout Session
```http
POST /api/billing/create-checkout-session
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "price_id": "price_xxx",
  "success_url": "http://localhost:3000/dashboard?success=true",
  "cancel_url": "http://localhost:3000/pricing?canceled=true"
}

Response:
{
  "session_id": "cs_test_xxx",
  "url": "https://checkout.stripe.com/..."
}
```

### Create Portal Session
```http
POST /api/billing/create-portal-session
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "return_url": "http://localhost:3000/settings"
}

Response:
{
  "url": "https://billing.stripe.com/..."
}
```

### Get Subscription Info
```http
GET /api/billing/subscription
Authorization: Bearer {access_token}

Response:
{
  "tier": "pro",
  "status": "active",
  "current_period_end": "2024-02-15T10:00:00Z",
  "cancel_at_period_end": false,
  "stripe_customer_id": "cus_xxx",
  "stripe_subscription_id": "sub_xxx"
}
```

### Webhook Endpoint
```http
POST /api/billing/webhook
Stripe-Signature: {signature}

Body: Stripe webhook event payload
```

---

## Database Schema

### User Model Updates
```python
class User(Base):
    # ... existing fields ...

    # Stripe fields
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True, index=True)

    # Subscription fields
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    subscription_status = Column(Enum(SubscriptionStatus), nullable=True)
    subscription_current_period_end = Column(DateTime, nullable=True)
    subscription_cancel_at_period_end = Column(Boolean, default=False)

    # Usage limits
    products_limit = Column(Integer, default=5)
    matches_limit = Column(Integer, default=10)
    alerts_limit = Column(Integer, default=1)
```

---

## Frontend Integration

### Pricing Page
Located at: `frontend/pages/pricing.js`

Features:
- Monthly/Yearly billing toggle
- 4 pricing tiers (Free, Pro, Business, Enterprise)
- Redirect to Stripe Checkout
- FAQ section

### Usage in Components
```javascript
import { useAuth } from '../context/AuthContext';

function MyComponent() {
  const { user } = useAuth();

  // Check subscription tier
  const isPro = user?.subscription_tier === 'pro';
  const canAddProduct = user?.products_limit > currentCount;

  // Upgrade prompt
  if (!canAddProduct) {
    return <UpgradePrompt />;
  }
}
```

---

## Testing with Stripe Test Cards

### Successful Payments
- **Visa:** 4242 4242 4242 4242
- **Mastercard:** 5555 5555 5555 4444
- **American Express:** 3782 822463 10005

### Failed Payments
- **Card declined:** 4000 0000 0000 0002
- **Insufficient funds:** 4000 0000 0000 9995
- **Expired card:** 4000 0000 0000 0069

### 3D Secure Authentication
- **Requires auth:** 4000 0025 0000 3155

### More test cards: https://stripe.com/docs/testing

---

## Webhook Event Handling

### Events We Handle

1. **`checkout.session.completed`**
   - Triggered when checkout is successful
   - Updates user with Stripe customer ID

2. **`customer.subscription.created`**
   - Triggered when subscription is created
   - Updates user tier and limits

3. **`customer.subscription.updated`**
   - Triggered when subscription changes (upgrade/downgrade)
   - Updates user tier and limits

4. **`customer.subscription.deleted`**
   - Triggered when subscription is cancelled
   - Downgrades user to FREE tier

5. **`invoice.payment_succeeded`**
   - Triggered when payment is successful
   - Sets subscription status to ACTIVE

6. **`invoice.payment_failed`**
   - Triggered when payment fails
   - Sets subscription status to PAST_DUE

---

## Production Deployment

### Environment Variables
Update your production `.env`:
```env
# Use live keys (starts with sk_live_ and pk_live_)
STRIPE_SECRET_KEY=sk_live_your_live_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_live_key

# Create new webhook with production domain
STRIPE_WEBHOOK_SECRET=whsec_your_production_secret
```

### Webhook Endpoint
Create a new webhook in Stripe Dashboard:
```
https://api.yourdomain.com/api/billing/webhook
```

### Security Checklist
- ✅ Use environment variables for all secrets
- ✅ Never commit API keys to version control
- ✅ Verify webhook signatures
- ✅ Use HTTPS for all webhook endpoints
- ✅ Rate limit webhook endpoint
- ✅ Log all webhook events
- ✅ Handle idempotency (Stripe may send same event multiple times)

---

## Troubleshooting

### Webhook Not Receiving Events
1. Check webhook URL is correct
2. Verify webhook secret in `.env`
3. Check Stripe Dashboard → Webhooks → Logs
4. For local testing, use Stripe CLI

### Subscription Not Updating
1. Check webhook is configured correctly
2. Look at backend logs for errors
3. Check Stripe Dashboard → Events for failed events
4. Verify database user has correct fields

### Payment Declined
1. Use test cards from Stripe documentation
2. Check if card requires 3D Secure authentication
3. Verify Stripe is in test mode

### Usage Limits Not Enforcing
1. Check `check_usage_limit()` is called in routes
2. Verify `user.products_limit` is set correctly
3. Check subscription tier mapping in `update_usage_limits()`

---

## Next Steps

1. **Add Settings Page** - Let users manage subscription from UI
2. **Usage Dashboard** - Show current usage vs limits
3. **Upgrade Prompts** - Show prompts when limits reached
4. **Invoice History** - Display past invoices
5. **Trial Management** - Add 14-day free trial logic
6. **Proration** - Handle mid-cycle upgrades/downgrades
7. **Team Billing** - Add workspace-level billing for Business/Enterprise

---

## Support

For Stripe-specific issues:
- Documentation: https://stripe.com/docs
- Support: https://support.stripe.com

For MarketIntel integration issues:
- Check the AUTHENTICATION-SETUP-GUIDE.md
- Review API documentation at http://localhost:8000/docs
