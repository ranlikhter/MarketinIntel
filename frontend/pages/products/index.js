import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import DataTable from '../../components/DataTable';
import { ConfirmModal } from '../../components/Modal';
import { useToast } from '../../components/Toast';
import { SkeletonTable } from '../../components/LoadingStates';
import api from '../../lib/api';

export default function ProductsPage() {
  const router = useRouter();
  const { addToast } = useToast();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteModal, setDeleteModal] = useState({ isOpen: false, product: null });

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const data = await api.getProducts();
      setProducts(data);
      setError(null);
      addToast(`Loaded ${data.length} products`, 'success');
    } catch (err) {
      setError('Failed to load products. Make sure the backend is running.');
      addToast('Failed to load products', 'error');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.deleteProduct(deleteModal.product.id);
      setProducts(products.filter(p => p.id !== deleteModal.product.id));
      addToast('Product deleted successfully', 'success');
    } catch (err) {
      addToast('Failed to delete product', 'error');
      console.error(err);
    }
  };

  const columns = [
    {
      header: 'Product',
      accessor: (row) => row.title,
      render: (row) => (
        <div className="flex items-center gap-3">
          {row.image_url && (
            <img
              src={row.image_url}
              alt={row.title}
              className="w-12 h-12 rounded-lg object-cover"
              onError={(e) => e.target.style.display = 'none'}
            />
          )}
          <div>
            <Link href={`/products/${row.id}`} className="font-medium text-primary-600 hover:text-primary-900">
              {row.title}
            </Link>
            {row.brand && (
              <p className="text-sm text-gray-500">{row.brand}</p>
            )}
          </div>
        </div>
      )
    },
    {
      header: 'SKU',
      accessor: (row) => row.sku || '-',
      sortable: true
    },
    {
      header: 'Competitors',
      accessor: (row) => row.competitor_count || 0,
      render: (row) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
          (row.competitor_count || 0) > 0
            ? 'bg-green-100 text-green-800'
            : 'bg-gray-100 text-gray-800'
        }`}>
          {row.competitor_count || 0} matches
        </span>
      ),
      sortable: true
    },
    {
      header: 'Added',
      accessor: (row) => new Date(row.created_at).toLocaleDateString(),
      sortable: true
    },
    {
      header: 'Actions',
      accessor: (row) => row.id,
      sortable: false,
      render: (row) => (
        <div className="flex items-center gap-2">
          <Link
            href={`/products/${row.id}`}
            className="text-primary-600 hover:text-primary-900 font-medium text-sm"
          >
            View
          </Link>
          <button
            onClick={() => setDeleteModal({ isOpen: true, product: row })}
            className="text-red-600 hover:text-red-900 font-medium text-sm"
          >
            Delete
          </button>
        </div>
      )
    }
  ];

  if (loading) {
    return (
      <Layout>
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="sm:flex sm:items-center mb-8">
            <div className="sm:flex-auto">
              <h1 className="text-3xl font-bold text-gray-900">Products</h1>
              <p className="mt-2 text-sm text-gray-700">
                Monitor your products across competitor websites
              </p>
            </div>
          </div>
          <SkeletonTable rows={5} />
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-red-800 font-semibold">{error}</p>
          </div>
          <p className="text-red-600 text-sm">
            Start the backend server: <code className="bg-red-100 px-2 py-1 rounded font-mono">start-backend.bat</code>
          </p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="sm:flex sm:items-center mb-8">
          <div className="sm:flex-auto">
            <h1 className="text-3xl font-bold text-gray-900">Products</h1>
            <p className="mt-2 text-sm text-gray-700">
              Monitor your products across competitor websites
            </p>
          </div>
          <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
            <Link
              href="/products/add"
              className="inline-flex items-center justify-center rounded-lg border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-all hover:scale-105"
            >
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Product
            </Link>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow-lg p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-100 text-sm font-medium">Total Products</p>
                <p className="text-3xl font-bold mt-2">{products.length}</p>
              </div>
              <div className="bg-white/20 p-3 rounded-lg">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg shadow-lg p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-100 text-sm font-medium">Total Matches</p>
                <p className="text-3xl font-bold mt-2">
                  {products.reduce((sum, p) => sum + (p.competitor_count || 0), 0)}
                </p>
              </div>
              <div className="bg-white/20 p-3 rounded-lg">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg shadow-lg p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-purple-100 text-sm font-medium">Avg. Matches/Product</p>
                <p className="text-3xl font-bold mt-2">
                  {products.length > 0
                    ? (products.reduce((sum, p) => sum + (p.competitor_count || 0), 0) / products.length).toFixed(1)
                    : '0.0'
                  }
                </p>
              </div>
              <div className="bg-white/20 p-3 rounded-lg">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Data Table */}
        {products.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow-lg">
            <svg
              className="mx-auto h-24 w-24 text-gray-300"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
              />
            </svg>
            <h3 className="mt-4 text-xl font-semibold text-gray-900">No products yet</h3>
            <p className="mt-2 text-gray-500 max-w-md mx-auto">
              Get started by adding your first product to monitor competitor pricing
            </p>
            <div className="mt-6">
              <Link
                href="/products/add"
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-primary-600 hover:bg-primary-700 shadow-lg hover:shadow-xl transition-all hover:scale-105"
              >
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add Your First Product
              </Link>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <DataTable
              columns={columns}
              data={products}
              searchable={true}
              sortable={true}
              pagination={true}
              pageSize={10}
              emptyMessage="No products found"
            />
          </div>
        )}

        {/* Delete Confirmation Modal */}
        <ConfirmModal
          isOpen={deleteModal.isOpen}
          onClose={() => setDeleteModal({ isOpen: false, product: null })}
          onConfirm={handleDelete}
          title="Delete Product"
          message={`Are you sure you want to delete "${deleteModal.product?.title}"? This action cannot be undone and will remove all associated competitor matches and price history.`}
          confirmText="Delete"
          cancelText="Cancel"
          type="danger"
        />
      </div>
    </Layout>
  );
}
