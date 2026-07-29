from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from curl_cffi import requests

BASE_URL = "https://medusa.tiendasdaka.com"
WEB_BASE_URL = "https://tiendasdaka.com/ve"
PUBLISHABLE_KEY = "pk_bd6711cd91e524a43eecba011b74c21d983186b6ee7be982a7d8fe523275f57b"

HEADERS = {
    "x-publishable-api-key": PUBLISHABLE_KEY,
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

TAG_MAP = {
    "ofertas": "ptag_01KEFWEJ90AFW49XEY59F7W9WD",
    "descuentos": "ptag_01KEFWEJ9061A5SEYJ7Y5KAWMF",
    "nuevos": "ptag_01KEFWEJ8ZNTAASRHVBAG6JTE5",
    "top": "ptag_01KEFWEJ903HE8BQNZ131S89N8",
    "envio-gratis": "ptag_01KEFWEJ90WFPWBXW1EA0CH4AE",
}


class DakaError(RuntimeError):
    """Excepción base para errores de Daka CLI."""


class DakaAPIError(DakaError):
    """Error al comunicarse con la API de Daka."""


class DakaProductNotFound(DakaError):
    """El producto solicitado no fue encontrado."""


@dataclass
class StoreBranch:
    id: str
    name: str
    city: str
    address: str
    opening_time: str
    closing_time: str
    latitude: str | None = None
    longitude: str | None = None

    @property
    def maps_url(self) -> str | None:
        if self.latitude and self.longitude:
            return f"https://maps.google.com/?q={self.latitude},{self.longitude}"
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoreBranch:
        open_t = data.get("openingTime")
        close_t = data.get("closingTime")
        open_str = f"{open_t // 100:02d}:00" if isinstance(open_t, int) else "08:00"
        close_str = f"{close_t // 100:02d}:00" if isinstance(close_t, int) else "19:00"

        addr = data.get("address", "").replace("\r", " ").replace("\n", " ").strip()
        addr = re.sub(r"\s+", " ", addr)

        return cls(
            id=data.get("id", ""),
            name=data.get("name", "").strip(),
            city=(data.get("city") or "Venezuela").strip(),
            address=addr,
            opening_time=open_str,
            closing_time=close_str,
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
        )


@dataclass
class Category:
    id: str
    name: str
    handle: str
    parent_category_id: str | None = None
    children: list[Category] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Category:
        raw_children = data.get("category_children", []) or []
        children = [cls.from_dict(c) for c in raw_children if isinstance(c, dict)]
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "").strip(),
            handle=data.get("handle", ""),
            parent_category_id=data.get("parent_category_id"),
            children=children,
        )


@dataclass
class ProductVariant:
    id: str
    title: str
    sku: str | None
    price_usd: float | None
    price_vef: float | None
    original_price_usd: float | None
    original_price_vef: float | None
    options: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductVariant:
        metadata = data.get("metadata") or {}
        price_meta = metadata.get("price_metadata") or {}
        usd = price_meta.get("usd") or {}
        vef = price_meta.get("vef") or {}

        opts_dict = {}
        for opt in data.get("options") or []:
            val = opt.get("value")
            opt_title = (opt.get("option") or {}).get("title") or "Opción"
            if val and opt_title:
                opts_dict[opt_title] = val

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            sku=data.get("sku"),
            price_usd=usd.get("finalPrice"),
            price_vef=vef.get("finalPrice"),
            original_price_usd=usd.get("originalPrice"),
            original_price_vef=vef.get("originalPrice"),
            options=opts_dict,
        )


@dataclass
class Product:
    id: str
    title: str
    handle: str
    description: str | None
    subtitle: str | None
    thumbnail: str | None
    images: list[str]
    categories: list[str]
    variants: list[ProductVariant]
    brand: str | None = None
    specifications: dict[str, str] = field(default_factory=dict)

    @property
    def main_variant(self) -> ProductVariant | None:
        return self.variants[0] if self.variants else None

    @property
    def price_usd(self) -> float | None:
        return self.main_variant.price_usd if self.main_variant else None

    @property
    def price_vef(self) -> float | None:
        return self.main_variant.price_vef if self.main_variant else None

    @property
    def original_price_usd(self) -> float | None:
        return self.main_variant.original_price_usd if self.main_variant else None

    @property
    def discount_percentage(self) -> float:
        if self.price_usd and self.original_price_usd and self.original_price_usd > self.price_usd:
            return round(((self.original_price_usd - self.price_usd) / self.original_price_usd) * 100, 1)
        return 0.0

    @property
    def has_discount(self) -> bool:
        return self.discount_percentage > 0.1

    @property
    def web_url(self) -> str:
        return f"{WEB_BASE_URL}/products/{self.handle}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Product:
        raw_images = data.get("images") or []
        images = [img.get("url") for img in raw_images if isinstance(img, dict) and img.get("url")]

        raw_cats = data.get("categories") or []
        categories = [cat.get("name") for cat in raw_cats if isinstance(cat, dict) and cat.get("name")]

        raw_variants = data.get("variants") or []
        variants = [ProductVariant.from_dict(v) for v in raw_variants if isinstance(v, dict)]

        specs = {}
        if variants and variants[0].options:
            specs = variants[0].options

        brand = specs.get("Marca") or data.get("metadata", {}).get("brand")

        return cls(
            id=data.get("id", ""),
            title=data.get("title", "").strip(),
            handle=data.get("handle", ""),
            description=data.get("description"),
            subtitle=data.get("subtitle"),
            thumbnail=data.get("thumbnail") or (images[0] if images else None),
            images=images,
            categories=categories,
            variants=variants,
            brand=brand,
            specifications=specs,
        )


class DakaClient:
    """Cliente para la API de Medusa de Tiendas Daka."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            res = requests.get(url, headers=HEADERS, params=params, impersonate="chrome", timeout=12)
            if res.status_code != 200:
                raise DakaAPIError(f"Error HTTP {res.status_code} al consultar {endpoint}")
            return res.json()
        except requests.RequestsError as e:
            raise DakaAPIError(f"No se pudo conectar con la API de Daka: {e}") from e

    def get_categories(self) -> list[Category]:
        """Obtiene todas las categorías de productos."""
        data = self._get("/store/product-categories")
        raw_categories = data.get("product_categories", [])
        return [Category.from_dict(c) for c in raw_categories]

    def search_products(
        self,
        query: str = "",
        category_id: str | None = None,
        tag_id: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        """Busca productos por texto, categoría, tag, rango de precio o criterio de ordenación."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if query:
            params["q"] = query
        if category_id:
            params["category_id[]"] = category_id
        if tag_id:
            params["tag_id[]"] = tag_id

        # Native Medusa sort orders
        if sort in ("nuevos", "-created_at"):
            params["order"] = "-created_at"
        elif sort in ("antiguos", "created_at"):
            params["order"] = "created_at"
        elif sort in ("nombre-asc", "title"):
            params["order"] = "title"
        elif sort in ("nombre-desc", "-title"):
            params["order"] = "-title"

        data = self._get("/store/products", params=params)
        raw_products = data.get("products", [])
        total = data.get("count", len(raw_products))

        products = [Product.from_dict(p) for p in raw_products]

        # Filter by price range if specified
        if min_price is not None:
            products = [p for p in products if p.price_usd is not None and p.price_usd >= min_price]
        if max_price is not None:
            products = [p for p in products if p.price_usd is not None and p.price_usd <= max_price]

        # Client-side price & discount sorting
        if sort in ("precio-asc", "precio_asc"):
            products.sort(key=lambda p: p.price_usd or 0.0)
        elif sort in ("precio-desc", "precio_desc"):
            products.sort(key=lambda p: p.price_usd or 0.0, reverse=True)
        elif sort in ("descuento", "oferta"):
            products.sort(key=lambda p: p.discount_percentage, reverse=True)

        return products, total

    def get_product_by_id(self, product_id: str) -> Product:
        """Obtiene un producto por su ID de Medusa."""
        try:
            data = self._get(f"/store/products/{product_id}")
            p_data = data.get("product")
            if not p_data:
                raise DakaProductNotFound(f"Producto con ID '{product_id}' no encontrado.")
            return Product.from_dict(p_data)
        except DakaAPIError as e:
            raise DakaProductNotFound(f"Producto con ID '{product_id}' no encontrado.") from e

    def get_product_by_handle(self, handle: str) -> Product:
        """Obtiene un producto por su handle / slug."""
        data = self._get("/store/products", params={"handle": handle})
        products = data.get("products", [])
        if not products:
            raise DakaProductNotFound(f"Producto con handle '{handle}' no encontrado.")
        return Product.from_dict(products[0])

    def get_product(self, identifier: str) -> Product:
        """Obtiene un producto recibiendo ID, handle o URL de Tiendas Daka."""
        clean_id = identifier.strip()

        if clean_id.startswith("http://") or clean_id.startswith("https://"):
            parsed = urlparse(clean_id)
            path_parts = [p for p in parsed.path.split("/") if p]
            if "products" in path_parts:
                idx = path_parts.index("products")
                if idx + 1 < len(path_parts):
                    clean_id = path_parts[idx + 1]

        if clean_id.startswith("prod_"):
            return self.get_product_by_id(clean_id)

        return self.get_product_by_handle(clean_id)

    def get_stores(self, city: str | None = None) -> list[StoreBranch]:
        """Obtiene todas las tiendas / sucursales físicas de Tiendas Daka."""
        try:
            res = requests.get(f"{WEB_BASE_URL}/stores-map", impersonate="chrome", timeout=10)
            start = res.text.find("branches")
            if start == -1:
                return []
            chunk = res.text[start:]
            arr_start = chunk.find("[")
            arr_end = chunk.find("]")
            raw_array = chunk[arr_start : arr_end + 1]
            clean_json = raw_array.replace("\\\\r", " ").replace("\\\\n", " ").replace("\\\\", "").replace('\\"', '"')
            stores_raw = json.loads(clean_json)

            branches = [StoreBranch.from_dict(s) for s in stores_raw]
            if city:
                city_lower = city.lower()
                branches = [b for b in branches if city_lower in b.city.lower() or city_lower in b.name.lower() or city_lower in b.address.lower()]
            return branches
        except Exception as e:
            raise DakaAPIError(f"No se pudieron cargar las tiendas físicas: {e}") from e

    def get_implied_bcv_rate(self) -> float:
        """Calcula la tasa de cambio implícita en Bs./USD muestreando productos."""
        products, _ = self.search_products(limit=10)
        rates = []
        for p in products:
            if p.price_usd and p.price_vef and p.price_usd > 0:
                rates.append(p.price_vef / p.price_usd)
        if rates:
            return round(sum(rates) / len(rates), 4)
        return 744.22
