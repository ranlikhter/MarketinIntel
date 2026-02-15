import { useState } from 'react';
import Layout from '../../components/Layout';
import ImportWizard from '../../components/ImportWizard';
import Modal from '../../components/Modal';

export default function IntegrationsPage() {
  const [showImportWizard, setShowImportWizard] = useState(false);

  const handleImportComplete = (result) => {
    setShowImportWizard(false);
    // Optionally redirect or refresh
  };

  return (
    <Layout>
      <div className="space-y-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Integrations</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Import products from your e-commerce platform or XML feed
          </p>
        </div>

        {/* Integration Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* XML Import */}
          <IntegrationCard
            icon={
              <svg className="w-16 h-16 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            }
            title="XML Feed"
            description="Upload an XML file with your product catalog. Supports Google Shopping Feed, WooCommerce exports, and custom formats."
            features={[
              'Auto-detect format',
              'Google Shopping Feed',
              'WooCommerce XML',
              'Custom XML formats'
            ]}
            buttonText="Import from XML"
            buttonColor="orange"
            onClick={() => setShowImportWizard(true)}
          />

          {/* WooCommerce */}
          <IntegrationCard
            icon={
              <svg className="w-16 h-16 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
              </svg>
            }
            title="WooCommerce"
            description="Connect directly to your WooCommerce store via REST API. Automatically sync all published products."
            features={[
              'Direct API connection',
              'Bulk import',
              'Filter by category',
              'Sync product status'
            ]}
            buttonText="Connect WooCommerce"
            buttonColor="purple"
            onClick={() => setShowImportWizard(true)}
          />

          {/* Shopify */}
          <IntegrationCard
            icon={
              <svg className="w-16 h-16 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            }
            title="Shopify"
            description="Connect to your Shopify store using Admin API. Import products, variants, and collections."
            features={[
              'Admin API integration',
              'Import all products',
              'Variant support',
              'Collection filtering'
            ]}
            buttonText="Connect Shopify"
            buttonColor="green"
            onClick={() => setShowImportWizard(true)}
          />
        </div>

        {/* How It Works */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-8 border border-blue-100">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Step
              number="1"
              title="Choose Source"
              description="Select XML, WooCommerce, or Shopify"
            />
            <Step
              number="2"
              title="Configure"
              description="Upload file or enter API credentials"
            />
            <Step
              number="3"
              title="Import"
              description="Products are validated and imported"
            />
            <Step
              number="4"
              title="Monitor"
              description="Start tracking competitor prices"
            />
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Feature
            icon={
              <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            }
            title="Fast Import"
            description="Import hundreds of products in seconds with our optimized batch processing"
          />
          <Feature
            icon={
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            }
            title="Duplicate Detection"
            description="Automatically skips products that already exist in your database"
          />
          <Feature
            icon={
              <svg className="w-8 h-8 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            }
            title="Automatic Sync"
            description="Keep products up-to-date with scheduled imports (coming soon)"
          />
          <Feature
            icon={
              <svg className="w-8 h-8 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            }
            title="Flexible Formats"
            description="Support for multiple XML formats with auto-detection"
          />
        </div>

        {/* CTA Section */}
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center border border-gray-100">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Ready to Import?</h2>
          <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
            Start monitoring competitor prices by importing your product catalog now
          </p>
          <button
            onClick={() => setShowImportWizard(true)}
            className="inline-flex items-center px-8 py-4 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-all hover:scale-105 shadow-lg"
          >
            <svg className="w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Start Import Wizard
          </button>
        </div>
      </div>

      {/* Import Wizard Modal */}
      <Modal
        isOpen={showImportWizard}
        onClose={() => setShowImportWizard(false)}
        title="Import Products"
        size="xl"
      >
        <ImportWizard onComplete={handleImportComplete} />
      </Modal>
    </Layout>
  );
}

function IntegrationCard({ icon, title, description, features, buttonText, buttonColor, onClick }) {
  const colorClasses = {
    orange: 'bg-orange-600 hover:bg-orange-700',
    purple: 'bg-purple-600 hover:bg-purple-700',
    green: 'bg-green-600 hover:bg-green-700'
  };

  return (
    <div className="bg-white rounded-xl shadow-lg hover:shadow-2xl transition-all p-8 border border-gray-100">
      <div className="flex justify-center mb-6">{icon}</div>
      <h3 className="text-2xl font-bold text-gray-900 mb-3 text-center">{title}</h3>
      <p className="text-gray-600 mb-6 text-center">{description}</p>

      <ul className="space-y-2 mb-6">
        {features.map((feature, idx) => (
          <li key={idx} className="flex items-center text-sm text-gray-700">
            <svg className="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            {feature}
          </li>
        ))}
      </ul>

      <button
        onClick={onClick}
        className={`w-full py-3 ${colorClasses[buttonColor]} text-white rounded-lg font-medium transition-all hover:scale-105 shadow-md`}
      >
        {buttonText}
      </button>
    </div>
  );
}

function Step({ number, title, description }) {
  return (
    <div className="text-center">
      <div className="w-12 h-12 bg-primary-600 text-white rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-3">
        {number}
      </div>
      <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
}

function Feature({ icon, title, description }) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-100 hover:shadow-lg transition-shadow">
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0">{icon}</div>
        <div>
          <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
          <p className="text-sm text-gray-600">{description}</p>
        </div>
      </div>
    </div>
  );
}
