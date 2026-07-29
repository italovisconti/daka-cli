from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir

from .client import Product


def get_cart_file_path() -> Path:
    config_dir = Path(user_config_dir("daka-cli"))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "cart.json"


@dataclass
class CartItem:
    id: str
    title: str
    handle: str
    price_usd: float
    quantity: int = 1
    thumbnail: str | None = None
    web_url: str | None = None

    @property
    def total_usd(self) -> float:
        return self.price_usd * self.quantity

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CartItem:
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            handle=data.get("handle", ""),
            price_usd=float(data.get("price_usd", 0.0)),
            quantity=int(data.get("quantity", 1)),
            thumbnail=data.get("thumbnail"),
            web_url=data.get("web_url"),
        )


@dataclass
class Cart:
    items: list[CartItem] = field(default_factory=list)

    @classmethod
    def load(cls) -> Cart:
        path = get_cart_file_path()
        if not path.exists():
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = [CartItem.from_dict(i) for i in data.get("items", [])]
                return cls(items=items)
        except Exception:
            return cls()

    def save(self) -> None:
        path = get_cart_file_path()
        data = {"items": [asdict(item) for item in self.items]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_product(self, product: Product, quantity: int = 1) -> CartItem:
        for item in self.items:
            if item.id == product.id or item.handle == product.handle:
                item.quantity += quantity
                self.save()
                return item

        new_item = CartItem(
            id=product.id,
            title=product.title,
            handle=product.handle,
            price_usd=product.price_usd or 0.0,
            quantity=quantity,
            thumbnail=product.thumbnail,
            web_url=product.web_url,
        )
        self.items.append(new_item)
        self.save()
        return new_item

    def remove_item(self, target: str) -> CartItem | None:
        target_lower = target.lower().strip()
        removed: CartItem | None = None

        # Intento 1: Coincidencia por índice (1-based)
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(self.items):
                removed = self.items.pop(idx)
                self.save()
                return removed

        # Intento 2: Coincidencia por ID, handle o título
        new_items = []
        for item in self.items:
            if not removed and (
                item.id.lower() == target_lower
                or item.handle.lower() == target_lower
                or target_lower in item.title.lower()
            ):
                removed = item
            else:
                new_items.append(item)

        if removed:
            self.items = new_items
            self.save()

        return removed

    def clear(self) -> None:
        self.items = []
        self.save()

    @property
    def grand_total_usd(self) -> float:
        return sum(item.total_usd for item in self.items)

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items)

    def export(self, filepath: Path | str, fmt: str, bcv_rate: float) -> str:
        out_path = Path(filepath)
        fmt = fmt.lower().strip()

        if fmt == "json":
            export_data = {
                "items": [
                    {
                        **asdict(item),
                        "total_usd": item.total_usd,
                        "total_vef": item.total_usd * bcv_rate,
                    }
                    for item in self.items
                ],
                "bcv_rate": bcv_rate,
                "grand_total_usd": self.grand_total_usd,
                "grand_total_vef": self.grand_total_usd * bcv_rate,
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

        elif fmt == "csv":
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Producto", "Handle", "Cantidad", "Precio USD", "Total USD", "Total VEF"])
                for item in self.items:
                    writer.writerow([
                        item.id,
                        item.title,
                        item.handle,
                        item.quantity,
                        f"{item.price_usd:.2f}",
                        f"{item.total_usd:.2f}",
                        f"{(item.total_usd * bcv_rate):.2f}",
                    ])
                writer.writerow([])
                writer.writerow(["", "", "", "", "TASA DAKA", f"1 USD = {bcv_rate:.2f} VEF", ""])
                writer.writerow(["", "", "", "", "TOTAL USD", f"${self.grand_total_usd:.2f}", ""])
                writer.writerow(["", "", "", "", "TOTAL VEF", f"Bs. {(self.grand_total_usd * bcv_rate):.2f}", ""])

        else:  # txt / md format
            lines = [
                "============================================",
                "       PRESUPUESTO / COTIZACIÓN DAKA        ",
                "============================================",
                f"Tasa de cambio Daka: 1 USD = {bcv_rate:,.2f} VEF",
                "--------------------------------------------",
            ]
            for idx, item in enumerate(self.items, 1):
                total_vef = item.total_usd * bcv_rate
                lines.append(
                    f"{idx}. {item.title}\n"
                    f"   Cant: {item.quantity} x ${item.price_usd:,.2f} = ${item.total_usd:,.2f} USD (Bs. {total_vef:,.2f})"
                )
            lines.extend([
                "--------------------------------------------",
                f"TOTAL EN USD: ${self.grand_total_usd:,.2f}",
                f"TOTAL EN VEF: Bs. {(self.grand_total_usd * bcv_rate):,.2f}",
                "============================================",
            ])
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

        return str(out_path.resolve())
