import { useState } from 'react';
import Layout from '../../components/Layout';
import ImportWizard from '../../components/ImportWizard';
import Modal from '../../components/Modal';

const Ico = {
  xml:      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>,
  store:    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>,
  cart:     <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" /></svg>,
  check:    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>,
  plus:     <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>,
  bolt:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  shield:   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
  sync:     <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  doc:      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
};

const INTEGRATIONS = [
  {
    icon: Ico.xml,
    iconBg: 'bg-orange-50 text-orange-600',
    title: 'XML Feed',
    desc: 'Upload a product catalog XML file. Supports Google Shopping Feed, WooCommerce exports, and custom formats.',
    features: ['Auto-detect format', 'Google Shopping Feed', 'WooCommerce XML', 'Custom XML formats'],
    button: 'Import from XML',
    btnClass: 'bg-orange-600 hover:bg-orange-700',
  },
  {
    icon: Ico.store,
    iconBg: 'bg-violet-50 text-violet-600',
    title: 'WooCommerce',
    desc: 'Connect to your WooCommerce store via REST API and automatically sync all published products.',
    features: ['Direct API connection', 'Bulk import', 'Filter by category', 'Sync product status'],
    button: 'Connect WooCommerce',
    btnClass: 'bg-violet-600 hover:bg-violet-700',
  },
  {
    icon: Ico.cart,
    iconBg: 'bg-emerald-50 text-emerald-600',
    title: 'Shopify',
    desc: 'Connect to your Shopify store using the Admin API. Import products, variants, and collections.',
    features: ['Admin API integration', 'Import all products', 'Variant support', 'Collection filtering'],
    button: 'Connect Shopify',
    btnClass: 'bg-emerald-600 hover:bg-emerald-700',
  },
];

const FEATURES = [
  { icon: Ico.bolt,   iconBg: 'bg-blue-50 text-blue-600',    title: 'Fast Import',          desc: 'Import hundreds of products in seconds with optimised batch processing.' },
  { icon: Ico.shield, iconBg: 'bg-emerald-50 text-emerald-600', title: 'Duplicate Detection', desc: 'Automatically skips products that already exist in your catalogue.' },
  { icon: Ico.sync,   iconBg: 'bg-violet-50 text-violet-600',  title: 'Automatic Sync',      desc: 'Keep products up-to-date with scheduled imports (coming soon).' },
  { icon: Ico.doc,    iconBg: 'bg-orange-50 text-orange-600',  title: 'Flexible Formats',    desc: 'Support for multiple XML formats with automatic field detection.' },
];

const STEPS = [
  { n: '1', title: 'Choose Source',  desc: 'Select XML, WooCommerce, or Shopify' },
  { n: '2', title: 'Configure',      desc: 'Upload file or enter API credentials' },
  { n: '3', title: 'Import',         desc: 'Products are validated and imported' },
  { n: '4', title: 'Monitor',        desc: 'Start tracking competitor prices' },
];

export default function IntegrationsPage() {
  const [showWizard, setShowWizard] = useState(false);

  return (
    <Layout>
      <div className="p-4 lg:p-6 space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Integrations</h1>
            <p className="text-sm text-gray-500 mt-0.5">Import products from your e-commerce platform or XML feed</p>
          </div>
          <button
            onClick={() => setShowWizard(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
          >
            {Ico.plus} Start Import
          </button>
        </div>

        {/* Integration Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {INTEGRATIONS.map((intg, i) => (
            <div key={i} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex flex-col gap-4">
              {/* Icon + title */}
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${intg.iconBg}`}>
                  {intg.icon}
                </div>
                <h3 className="text-base font-bold text-gray-900">{intg.title}</h3>
              </div>

              <p className="text-xs text-gray-500 leading-relaxed">{intg.desc}</p>

              {/* Features */}
              <ul className="space-y-1.5">
                {intg.features.map((f, j) => (
                  <li key={j} className="flex items-center gap-2 text-xs text-gray-700">
                    <span className="text-emerald-500 shrink-0">{Ico.check}</span>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => setShowWizard(true)}
                className={`mt-auto w-full py-2.5 text-white text-sm font-medium rounded-xl transition-colors ${intg.btnClass}`}
              >
                {intg.button}
              </button>
            </div>
          ))}
        </div>

        {/* How It Works */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-50">
            <h2 className="text-sm font-semibold text-gray-900">How It Works</h2>
          </div>
          <div className="p-5 grid grid-cols-2 lg:grid-cols-4 gap-4">
            {STEPS.map((s, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-8 h-8 bg-blue-600 text-white rounded-xl flex items-center justify-center text-sm font-bold shrink-0">
                  {s.n}
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{s.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {FEATURES.map((f, i) => (
            <div key={i} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-start gap-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${f.iconBg}`}>{f.icon}</div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{f.title}</p>
                <p className="text-xs text-gray-500 mt-1">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>

      </div>

      {/* Import Wizard Modal */}
      <Modal isOpen={showWizard} onClose={() => setShowWizard(false)} title="Import Products" size="xl">
        <ImportWizard onComplete={() => setShowWizard(false)} />
      </Modal>
    </Layout>
  );
}
