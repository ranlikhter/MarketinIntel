import { useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';

export default function Pricing() {
  const [billingPeriod, setBillingPeriod] = useState('monthly'); // 'monthly' or 'yearly'
  const [loading, setLoading] = useState(null);
  const { user, isAuthenticated } = useAuth();
  const router = useRouter();

  const plans = [
    {
      name: 'Free',
      price: { monthly: 0, yearly: 0 },
      priceId: { monthly: null, yearly: null },
      description: 'Perfect for trying out MarketIntel',
      features: [
        '5 products monitored',
        '10 AI-powered matches',
        '1 price alert',
        'Basic analytics',
        'Email support',
        '7-day price history',
      ],
      cta: 'Get Started',
      popular: false,
    },
    {
      name: 'Pro',
      price: { monthly: 49, yearly: 490 }, // $490/year = $40.83/month (17% savings)
      priceId: {
        monthly: 'price_pro_monthly',
        yearly: 'price_pro_yearly',
      },
      description: 'For individuals and small teams',
      features: [
        '50 products monitored',
        '100 AI-powered matches',
        '10 price alerts',
        'Advanced analytics & insights',
        'Priority email support',
        '30-day price history',
        'API access (1,000 calls/month)',
        'Export to CSV/Excel',
        'Custom scraping schedules',
      ],
      cta: 'Start Free Trial',
      popular: true,
    },
    {
      name: 'Business',
      price: { monthly: 149, yearly: 1490 }, // $1490/year = $124.17/month (17% savings)
      priceId: {
        monthly: 'price_business_monthly',
        yearly: 'price_business_yearly',
      },
      description: 'For growing businesses',
      features: [
        '200 products monitored',
        '500 AI-powered matches',
        '50 price alerts',
        'Advanced analytics & insights',
        'Priority support + Slack integration',
        '90-day price history',
        'API access (10,000 calls/month)',
        'Team workspace (5 members)',
        'White-label reports',
        'Custom integrations',
        'Dedicated account manager',
      ],
      cta: 'Start Free Trial',
      popular: false,
    },
    {
      name: 'Enterprise',
      price: { monthly: 499, yearly: 4990 },
      priceId: {
        monthly: 'price_enterprise_monthly',
        yearly: 'price_enterprise_yearly',
      },
      description: 'For large organizations',
      features: [
        'Unlimited products',
        'Unlimited AI matches',
        'Unlimited alerts',
        'Enterprise analytics & BI',
        '24/7 phone + Slack support',
        'Unlimited price history',
        'Unlimited API access',
        'Unlimited team members',
        'Custom branding',
        'SSO / SAML',
        'SLA guarantee',
        'Dedicated infrastructure',
        'Custom development',
      ],
      cta: 'Contact Sales',
      popular: false,
    },
  ];

  const handleSubscribe = async (plan) => {
    if (plan.name === 'Free') {
      router.push('/auth/signup');
      return;
    }

    if (plan.name === 'Enterprise') {
      window.location.href = 'mailto:sales@marketintel.com?subject=Enterprise Plan Inquiry';
      return;
    }

    if (!isAuthenticated) {
      router.push(`/auth/signup?plan=${plan.name.toLowerCase()}`);
      return;
    }

    setLoading(plan.name);

    try {
      const priceId = billingPeriod === 'yearly' ? plan.priceId.yearly : plan.priceId.monthly;

      const response = await fetch('http://localhost:8000/api/billing/create-checkout-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
        body: JSON.stringify({
          price_id: priceId,
          success_url: `${window.location.origin}/dashboard?success=true`,
          cancel_url: `${window.location.origin}/pricing?canceled=true`,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Redirect to Stripe Checkout
        window.location.href = data.url;
      } else {
        alert('Failed to start checkout: ' + (data.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Checkout error:', error);
      alert('Failed to start checkout');
    } finally {
      setLoading(null);
    }
  };

  return (
    <Layout>
      <div className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-extrabold text-white sm:text-5xl sm:tracking-tight lg:text-6xl">
              Simple, transparent pricing
            </h1>
            <p className="mt-5 text-xl text-white/60">
              Choose the plan that&apos;s right for your business
            </p>

            {/* Billing Period Toggle */}
            <div className="mt-8 flex items-center justify-center space-x-4">
              <span className={`text-base font-medium ${billingPeriod === 'monthly' ? 'text-white' : 'text-white/40'}`}>
                Monthly
              </span>
              <button
                onClick={() => setBillingPeriod(billingPeriod === 'monthly' ? 'yearly' : 'monthly')}
                className="relative inline-flex h-6 w-11 items-center rounded-full bg-amber-500 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2"
              >
                <span
                  className={`${
                    billingPeriod === 'yearly' ? 'translate-x-6' : 'translate-x-1'
                  } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                />
              </button>
              <span className={`text-base font-medium ${billingPeriod === 'yearly' ? 'text-white' : 'text-white/40'}`}>
                Yearly
                <span className="ml-2 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium" style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399' }}>
                  Save 17%
                </span>
              </span>
            </div>
          </div>

          {/* Pricing Cards */}
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`relative rounded-2xl shadow-xl transition-transform hover:scale-105 ${
                  plan.popular ? 'ring-2 ring-amber-400' : ''
                }`}
                style={{ background: 'var(--bg-elevated)', border: plan.popular ? undefined : '1px solid var(--border)' }}
              >
                {plan.popular && (
                  <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2">
                    <span className="inline-flex items-center rounded-full gradient-brand px-4 py-1 text-xs font-semibold text-white shadow-lg">
                      MOST POPULAR
                    </span>
                  </div>
                )}

                <div className="p-8">
                  <h3 className="text-2xl font-bold text-white">{plan.name}</h3>
                  <p className="mt-2 text-sm text-white/50">{plan.description}</p>

                  <div className="mt-6">
                    <div className="flex items-baseline">
                      <span className="text-5xl font-extrabold text-white">
                        ${plan.price[billingPeriod] === 0 ? '0' : plan.price[billingPeriod]}
                      </span>
                      {plan.price[billingPeriod] > 0 && (
                        <span className="ml-2 text-base font-medium text-white/50">
                          /{billingPeriod === 'yearly' ? 'year' : 'month'}
                        </span>
                      )}
                    </div>
                    {billingPeriod === 'yearly' && plan.price.yearly > 0 && (
                      <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
                        ${(plan.price.yearly / 12).toFixed(2)}/month billed annually
                      </p>
                    )}
                  </div>

                  <button
                    onClick={() => handleSubscribe(plan)}
                    disabled={loading === plan.name}
                    className={`mt-8 w-full py-3 px-6 rounded-lg font-semibold transition duration-150 ${
                      plan.popular
                        ? 'gradient-brand text-white hover:opacity-90 shadow-lg'
                        : 'text-white hover:bg-white/5'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                    style={!plan.popular ? { border: '1px solid var(--border)' } : {}}
                  >
                    {loading === plan.name ? 'Loading...' : plan.cta}
                  </button>

                  <ul className="mt-8 space-y-4">
                    {plan.features.map((feature, index) => (
                      <li key={index} className="flex items-start">
                        <svg
                          className="h-5 w-5 text-green-400 mr-3 mt-0.5 flex-shrink-0"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                        <span className="text-sm text-white/70">{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>

          {/* FAQ Section */}
          <div className="mt-20">
            <h2 className="text-3xl font-bold text-center text-white mb-8">
              Frequently Asked Questions
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Can I change plans later?
                </h3>
                <p className="text-white/50">
                  Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately.
                </p>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Is there a free trial?
                </h3>
                <p className="text-white/50">
                  Yes, all paid plans come with a 14-day free trial. No credit card required.
                </p>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  What payment methods do you accept?
                </h3>
                <p className="text-white/50">
                  We accept all major credit cards, debit cards, and ACH transfers for Enterprise plans.
                </p>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Can I cancel anytime?
                </h3>
                <p className="text-white/50">
                  Yes, you can cancel your subscription at any time. You&apos;ll have access until the end of your billing period.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
