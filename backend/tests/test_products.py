import unittest
from app import app

class TestProductEndpoints(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_create_product(self):
        response = self.app.post('/products', json={
            'name': 'Test Product',
            'price': 100.0,
            'description': 'A product for testing.'
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn(b'Test Product', response.data)

    def test_get_products(self):
        response = self.app.get('/products')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)

    def test_competitor_matching(self):
        response = self.app.post('/products/match', json={
            'product_id': '123',
            'competitor_id': '456'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Matching competitors found', response.data)

if __name__ == '__main__':
    unittest.main()