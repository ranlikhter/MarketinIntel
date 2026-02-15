import { useState } from 'react';
import { useToast } from './Toast';
import { LoadingSpinner } from './LoadingStates';
import api from '../lib/api';

export default function ImportWizard({ onComplete }) {
  const { addToast } = useToast();
  const [step, setStep] = useState(1);
  const [importing, setImporting] = useState(false);
  const [importType, setImportType] = useState(null);

  const [xmlFile, setXmlFile] = useState(null);
  const [xmlFormat, setXmlFormat] = useState('auto');

  const [woocommerce, setWoocommerce] = useState({
    storeUrl: '',
    consumerKey: '',
    consumerSecret: '',
    importLimit: 100
  });

  const [shopify, setShopify] = useState({
    shopUrl: '',
    accessToken: '',
    importLimit: 100
  });

  const handleTypeSelect = (type) => {
    setImportType(type);
    setStep(2);
  };

  const handleXMLImport = async () => {
    if (!xmlFile) {
      addToast('Please select an XML file', 'warning');
      return;
    }

    setImporting(true);

    try {
      const result = await api.importFromXML(xmlFile, xmlFormat);

      if (result.success) {
        addToast(`Successfully imported ${result.products_imported} products!`, 'success');
        if (result.products_skipped > 0) {
          addToast(`Skipped ${result.products_skipped} duplicate products`, 'info');
        }
        if (onComplete) onComplete(result);
        setStep(3);
      } else {
        addToast('Import failed: ' + (result.errors[0] || 'Unknown error'), 'error');
      }
    } catch (error) {
      addToast('Import failed: ' + error.message, 'error');
    } finally {
      setImporting(false);
    }
  };

  const handleWooCommerceImport = async () => {
    if (!woocommerce.storeUrl || !woocommerce.consumerKey || !woocommerce.consumerSecret) {
      addToast('Please fill in all WooCommerce credentials', 'warning');
      return;
    }

    setImporting(true);

    try {
      const result = await api.importFromWooCommerce(
        woocommerce.storeUrl,
        woocommerce.consumerKey,
        woocommerce.consumerSecret,
        woocommerce.importLimit
      );

      if (result.success) {
        addToast(`Successfully imported ${result.products_imported} products!`, 'success');
        if (result.products_skipped > 0) {
          addToast(`Skipped ${result.products_skipped} duplicate products`, 'info');
        }
        if (onComplete) onComplete(result);
        setStep(3);
      } else {
        addToast('Import failed: ' + (result.errors[0] || 'Unknown error'), 'error');
      }
    } catch (error) {
      addToast('Import failed: ' + error.message, 'error');
    } finally {
      setImporting(false);
    }
  };

  const handleShopifyImport = async () => {
    if (!shopify.shopUrl || !shopify.accessToken) {
      addToast('Please fill in all Shopify credentials', 'warning');
      return;
    }

    setImporting(true);

    try {
      const result = await api.importFromShopify(
        shopify.shopUrl,
        shopify.accessToken,
        shopify.importLimit
      );

      if (result.success) {
        addToast(`Successfully imported ${result.products_imported} products!`, 'success');
        if (result.products_skipped > 0) {
          addToast(`Skipped ${result.products_skipped} duplicate products`, 'info');
        }
        if (onComplete) onComplete(result);
        setStep(3);
      } else {
        addToast('Import failed: ' + (result.errors[0] || 'Unknown error'), 'error');
      }
    } catch (error) {
      addToast('Import failed: ' + error.message, 'error');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center flex-1">
              <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                step >= s ? 'bg-primary-600 border-primary-600 text-white' : 'border-gray-300 text-gray-500'
              }`}>
                {step > s ? (
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span className="font-semibold">{s}</span>
                )}
              </div>
              {s < 3 && (
                <div className={`flex-1 h-1 mx-2 ${step > s ? 'bg-primary-600' : 'bg-gray-300'}`} />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between mt-2">
          <span className={`text-sm ${step >= 1 ? 'text-primary-600 font-medium' : 'text-gray-500'}`}>
            Choose Source
          </span>
          <span className={`text-sm ${step >= 2 ? 'text-primary-600 font-medium' : 'text-gray-500'}`}>
            Configure
          </span>
          <span className={`text-sm ${step >= 3 ? 'text-primary-600 font-medium' : 'text-gray-500'}`}>
            Complete
          </span>
        </div>
      </div>

      {/* Step 1: Choose Import Type */}
      {step === 1 && (
        <div className="space-y-6">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Import Products</h2>
            <p className="text-gray-600">Choose your import source to get started</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <ImportTypeCard
              icon={
                <svg className="w-12 h-12 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              }
              title="XML File"
              description="Upload an XML file containing your product catalog"
              onClick={() => handleTypeSelect('xml')}
            />

            <ImportTypeCard
              icon={
                <svg className="w-12 h-12 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
              }
              title="WooCommerce"
              description="Connect to your WooCommerce store and sync products"
              onClick={() => handleTypeSelect('woocommerce')}
            />

            <ImportTypeCard
              icon={
                <svg className="w-12 h-12 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              }
              title="Shopify"
              description="Connect to your Shopify store and import products"
              onClick={() => handleTypeSelect('shopify')}
            />
          </div>
        </div>
      )}

      {/* Step 2: Configure */}
      {step === 2 && (
        <div className="bg-white rounded-lg shadow-lg p-8">
          <button
            onClick={() => setStep(1)}
            className="mb-6 text-primary-600 hover:text-primary-700 font-medium text-sm flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>

          {importType === 'xml' && (
            <XMLImportForm
              file={xmlFile}
              format={xmlFormat}
              onFileChange={setXmlFile}
              onFormatChange={setXmlFormat}
              onImport={handleXMLImport}
              importing={importing}
            />
          )}

          {importType === 'woocommerce' && (
            <WooCommerceImportForm
              data={woocommerce}
              onChange={setWoocommerce}
              onImport={handleWooCommerceImport}
              importing={importing}
            />
          )}

          {importType === 'shopify' && (
            <ShopifyImportForm
              data={shopify}
              onChange={setShopify}
              onImport={handleShopifyImport}
              importing={importing}
            />
          )}
        </div>
      )}

      {/* Step 3: Complete */}
      {step === 3 && (
        <div className="text-center py-12 bg-white rounded-lg shadow-lg">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-12 h-12 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Import Complete!</h2>
          <p className="text-gray-600 mb-8">Your products have been successfully imported</p>
          <button
            onClick={() => window.location.href = '/products'}
            className="inline-flex items-center px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
          >
            View Products
            <svg className="w-5 h-5 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

function ImportTypeCard({ icon, title, description, onClick }) {
  return (
    <button
      onClick={onClick}
      className="bg-white rounded-lg shadow-md hover:shadow-xl transition-all p-8 text-center border-2 border-transparent hover:border-primary-500 hover:scale-105"
    >
      <div className="flex justify-center mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </button>
  );
}

function XMLImportForm({ file, format, onFileChange, onFormatChange, onImport, importing }) {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-gray-900">Upload XML File</h3>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          XML File
        </label>
        <input
          type="file"
          accept=".xml"
          onChange={(e) => onFileChange(e.target.files[0])}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
        />
        {file && (
          <p className="mt-2 text-sm text-gray-600">Selected: {file.name}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          XML Format
        </label>
        <select
          value={format}
          onChange={(e) => onFormatChange(e.target.value)}
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
        >
          <option value="auto">Auto-detect</option>
          <option value="google_shopping">Google Shopping Feed</option>
          <option value="woocommerce">WooCommerce Export</option>
          <option value="custom">Custom Format</option>
        </select>
      </div>

      <button
        onClick={onImport}
        disabled={importing || !file}
        className="w-full inline-flex items-center justify-center px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {importing ? (
          <>
            <LoadingSpinner size="sm" color="white" />
            <span className="ml-2">Importing...</span>
          </>
        ) : (
          'Import Products'
        )}
      </button>
    </div>
  );
}

function WooCommerceImportForm({ data, onChange, onImport, importing }) {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-gray-900">Connect WooCommerce</h3>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Store URL
        </label>
        <input
          type="url"
          value={data.storeUrl}
          onChange={(e) => onChange({ ...data, storeUrl: e.target.value })}
          placeholder="https://yourstore.com"
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Consumer Key
        </label>
        <input
          type="text"
          value={data.consumerKey}
          onChange={(e) => onChange({ ...data, consumerKey: e.target.value })}
          placeholder="ck_xxxxx"
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Consumer Secret
        </label>
        <input
          type="password"
          value={data.consumerSecret}
          onChange={(e) => onChange({ ...data, consumerSecret: e.target.value })}
          placeholder="cs_xxxxx"
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Import Limit
        </label>
        <input
          type="number"
          value={data.importLimit}
          onChange={(e) => onChange({ ...data, importLimit: parseInt(e.target.value) })}
          min="1"
          max="1000"
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
        />
      </div>

      <button
        onClick={onImport}
        disabled={importing}
        className="w-full inline-flex items-center justify-center px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {importing ? (
          <>
            <LoadingSpinner size="sm" color="white" />
            <span className="ml-2">Importing...</span>
          </>
        ) : (
          'Import Products'
        )}
      </button>
    </div>
  );
}

function ShopifyImportForm({ data, onChange, onImport, importing }) {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-gray-900">Connect Shopify</h3>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Shop URL
        </label>
        <input
          type="text"
          value={data.shopUrl}
          onChange={(e) => onChange({ ...data, shopUrl: e.target.value })}
          placeholder="your-store.myshopify.com"
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Admin API Access Token
        </label>
        <input
          type="password"
          value={data.accessToken}
          onChange={(e) => onChange({ ...data, accessToken: e.target.value })}
          placeholder="shpat_xxxxx"
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Import Limit
        </label>
        <input
          type="number"
          value={data.importLimit}
          onChange={(e) => onChange({ ...data, importLimit: parseInt(e.target.value) })}
          min="1"
          max="1000"
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
        />
      </div>

      <button
        onClick={onImport}
        disabled={importing}
        className="w-full inline-flex items-center justify-center px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {importing ? (
          <>
            <LoadingSpinner size="sm" color="white" />
            <span className="ml-2">Importing...</span>
          </>
        ) : (
          'Import Products'
        )}
      </button>
    </div>
  );
}
