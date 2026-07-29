import unittest
from daka_cli.client import Category, DakaClient, Product, ProductVariant, StoreBranch


class TestDakaClient(unittest.TestCase):

    def test_category_parsing(self):
        raw_cat = {
            "id": "pcat_123",
            "name": " Audio y Video ",
            "handle": "audio-y-video",
            "parent_category_id": None,
            "category_children": [
                {
                    "id": "pcat_456",
                    "name": "Televisores",
                    "handle": "televisores",
                    "parent_category_id": "pcat_123",
                }
            ],
        }
        cat = Category.from_dict(raw_cat)
        self.assertEqual(cat.id, "pcat_123")
        self.assertEqual(cat.name, "Audio y Video")
        self.assertEqual(len(cat.children), 1)
        self.assertEqual(cat.children[0].name, "Televisores")

    def test_product_parsing(self):
        raw_product = {
            "id": "prod_789",
            "title": " Televisor 55  ",
            "handle": "televisor-55",
            "description": "Smart TV 4K",
            "images": [{"url": "https://example.com/tv.jpg"}],
            "categories": [{"name": "Televisores"}],
            "variants": [
                {
                    "id": "var_1",
                    "title": "Televisor 55",
                    "sku": "TV-55",
                    "metadata": {
                        "price_metadata": {
                            "usd": {"finalPrice": 450.0, "originalPrice": 500.0},
                            "vef": {"finalPrice": 335000.0, "originalPrice": 372000.0},
                        }
                    },
                    "options": [
                        {
                            "value": "4K",
                            "option": {"title": "Resolución"},
                        }
                    ],
                }
            ],
        }
        prod = Product.from_dict(raw_product)
        self.assertEqual(prod.id, "prod_789")
        self.assertEqual(prod.title, "Televisor 55")
        self.assertEqual(prod.price_usd, 450.0)
        self.assertEqual(prod.original_price_usd, 500.0)
        self.assertTrue(prod.has_discount)
        self.assertEqual(prod.discount_percentage, 10.0)
        self.assertEqual(prod.web_url, "https://tiendasdaka.com/ve/products/televisor-55")
        self.assertEqual(prod.specifications.get("Resolución"), "4K")

    def test_store_branch_parsing(self):
        data = {
            "id": "sloc_1",
            "name": "Sucursal Bello Monte",
            "city": "Caracas",
            "address": "Av. Principal\r\nColinas de Bello Monte",
            "openingTime": 800,
            "closingTime": 1900,
            "latitude": "10.48",
            "longitude": "-66.88",
        }
        store = StoreBranch.from_dict(data)
        self.assertEqual(store.name, "Sucursal Bello Monte")
        self.assertEqual(store.city, "Caracas")
        self.assertEqual(store.opening_time, "08:00")
        self.assertEqual(store.closing_time, "19:00")
        self.assertEqual(store.maps_url, "https://maps.google.com/?q=10.48,-66.88")

    def test_product_identifier_url_extraction(self):
        client = DakaClient()
        handle = "televisor-32-pulgadas-hd-smart-slim-hyundai"
        url = f"https://tiendasdaka.com/ve/products/{handle}"
        called_handle = []

        def mock_get_by_handle(h):
            called_handle.append(h)
            return Product(
                id="prod_1", title="TV", handle=h, description=None, subtitle=None, thumbnail=None, images=[], categories=[], variants=[]
            )

        client.get_product_by_handle = mock_get_by_handle
        p = client.get_product(url)
        self.assertEqual(called_handle[0], handle)
        self.assertEqual(p.handle, handle)


if __name__ == "__main__":
    unittest.main()
