import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        {/* Favicon */}
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
        <link rel="icon" type="image/png" href="/icons/icon-192.png" />

        {/* PWA manifest */}
        <link rel="manifest" href="/manifest.json" />

        {/* PWA meta */}
        <meta name="theme-color" content="#2563eb" />
        <meta name="application-name" content="MarketIntel" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="MarketIntel" />
        <meta name="mobile-web-app-capable" content="yes" />

        {/* Apple touch icon */}
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />

        {/* SEO */}
        <meta name="description" content="Real-time competitive price intelligence and monitoring for e-commerce businesses." />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  )
}
