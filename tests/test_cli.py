import json
import unittest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from daka_cli.cli import app
from daka_cli.client import Product, ProductVariant, StoreBranch

runner = CliRunner()


class TestDakaCLI(unittest.TestCase):

    def test_cli_version(self):
        result = runner.invoke(app, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("daka-cli v", result.stdout)

    @patch("daka_cli.cli.DakaClient")
    def test_cli_buscar_json(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        mock_product = Product(
            id="prod_123",
            title="Televisor LG",
            handle="televisor-lg",
            description="Smart TV",
            subtitle=None,
            thumbnail=None,
            images=[],
            categories=["Audio y Video"],
            variants=[
                ProductVariant(
                    id="var_1",
                    title="Televisor LG",
                    sku="LG-123",
                    price_usd=300.0,
                    price_vef=220000.0,
                    original_price_usd=300.0,
                    original_price_vef=220000.0,
                )
            ],
        )
        mock_instance.search_products.return_value = ([mock_product], 1)

        result = runner.invoke(app, ["buscar", "televisor", "--json", "-s", "precio-asc"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["query"], "televisor")
        self.assertEqual(len(data["products"]), 1)
        self.assertEqual(data["products"][0]["title"], "Televisor LG")

    @patch("daka_cli.cli.DakaClient")
    def test_cli_tiendas_json(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        store = StoreBranch(
            id="sloc_1",
            name="Sucursal Bello Monte",
            city="Caracas",
            address="Av. Principal",
            opening_time="08:00",
            closing_time="19:00",
        )
        mock_instance.get_stores.return_value = [store]

        result = runner.invoke(app, ["tiendas", "--json"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.stdout)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Sucursal Bello Monte")

    @patch("daka_cli.cli.DakaClient")
    def test_cli_bcv(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.get_implied_bcv_rate.return_value = 744.25

        result = runner.invoke(app, ["bcv", "100"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("1 USD = 744.25 VEF", result.stdout)


if __name__ == "__main__":
    unittest.main()
