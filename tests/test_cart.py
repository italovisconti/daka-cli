from pathlib import Path
from unittest.mock import patch

from daka_cli.cart import Cart, CartItem
from daka_cli.client import Product


def test_cart_add_and_remove(tmp_path: Path):
    cart_file = tmp_path / "cart.json"
    with patch("daka_cli.cart.get_cart_file_path", return_value=cart_file):
        cart = Cart.load()
        assert len(cart.items) == 0

        product = Product(
            id="prod_123",
            title="TV Smart 55",
            handle="tv-smart-55",
            price_usd=300.0,
            web_url="https://daka.com/tv-smart-55",
        )

        cart.add_product(product, quantity=2)
        assert len(cart.items) == 1
        assert cart.grand_total_usd == 600.0
        assert cart.total_items == 2

        # Add again increases quantity
        cart.add_product(product, quantity=1)
        assert cart.total_items == 3
        assert cart.grand_total_usd == 900.0

        # Remove item
        removed = cart.remove_item("1")
        assert removed is not None
        assert removed.id == "prod_123"
        assert len(cart.items) == 0


def test_cart_export(tmp_path: Path):
    cart_file = tmp_path / "cart.json"
    csv_out = tmp_path / "presupuesto.csv"
    json_out = tmp_path / "presupuesto.json"
    txt_out = tmp_path / "presupuesto.txt"

    with patch("daka_cli.cart.get_cart_file_path", return_value=cart_file):
        cart = Cart.load()
        product = Product(
            id="prod_999",
            title="Nevera Midea",
            handle="nevera-midea",
            price_usd=400.0,
        )
        cart.add_product(product, quantity=1)

        cart.export(csv_out, fmt="csv", bcv_rate=50.0)
        assert csv_out.exists()
        assert "Nevera Midea" in csv_out.read_text(encoding="utf-8")

        cart.export(json_out, fmt="json", bcv_rate=50.0)
        assert json_out.exists()
        assert "grand_total_vef" in json_out.read_text(encoding="utf-8")

        cart.export(txt_out, fmt="txt", bcv_rate=50.0)
        assert txt_out.exists()
        assert "PRESUPUESTO / COTIZACIÓN DAKA" in txt_out.read_text(encoding="utf-8")
