"""
Catalogue management module for BarcodeReader.

Handles loading, validating, resolving, and querying categories and products
from JSON data storage. Barcode lookup logic is kept strictly isolated
from API routes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class CatalogueError(Exception):
    """Base exception for catalogue operations."""


class ProductNotFoundError(CatalogueError):
    """Raised when a barcode cannot be matched to any product."""


class InvalidBarcodeError(CatalogueError):
    """Raised when the barcode input is empty or malformed."""


class Catalogue:
    """Manages product and category catalogues loaded from JSON storage."""

    def __init__(
        self,
        categories_path: Optional[Path | str] = None,
        products_path: Optional[Path | str] = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent
        self.categories_path = (
            Path(categories_path)
            if categories_path
            else base_dir / "data" / "categories.json"
        )
        self.products_path = (
            Path(products_path)
            if products_path
            else base_dir / "data" / "products.json"
        )
        self._categories: List[Dict[str, Any]] = []
        self._products: List[Dict[str, Any]] = []
        self._categories_by_id: Dict[int, Dict[str, Any]] = {}
        self._products_by_barcode: Dict[str, Dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        """Reload and parse data files from disk, then validate integrity."""
        if not self.categories_path.exists():
            raise FileNotFoundError(
                f"Categories file not found: {self.categories_path}"
            )
        if not self.products_path.exists():
            raise FileNotFoundError(
                f"Products file not found: {self.products_path}"
            )

        with open(self.categories_path, "r", encoding="utf-8") as f:
            self._categories = json.load(f)

        with open(self.products_path, "r", encoding="utf-8") as f:
            self._products = json.load(f)

        self._index_and_validate()

    def _index_and_validate(self) -> None:
        """Index categories and products while verifying uniqueness and integrity."""
        self._categories_by_id = {}
        for cat in self._categories:
            cat_id = cat.get("id")
            if cat_id is None:
                raise ValueError(f"Category entry missing 'id': {cat}")
            if cat_id in self._categories_by_id:
                raise ValueError(f"Duplicate category ID detected: {cat_id}")
            self._categories_by_id[cat_id] = cat

        self._products_by_barcode = {}
        seen_product_ids = set()

        for prod in self._products:
            prod_id = prod.get("id")
            barcode = prod.get("barcode")
            cat_id = prod.get("category_id")

            if not prod_id:
                raise ValueError(f"Product missing 'id': {prod}")
            if prod_id in seen_product_ids:
                raise ValueError(f"Duplicate product ID detected: {prod_id}")
            seen_product_ids.add(prod_id)

            if not barcode or not isinstance(barcode, str) or not barcode.strip():
                raise ValueError(f"Product has invalid barcode: {prod}")
            barcode_clean = barcode.strip()
            if barcode_clean in self._products_by_barcode:
                raise ValueError(f"Duplicate barcode detected: {barcode_clean}")

            if cat_id not in self._categories_by_id:
                raise ValueError(
                    f"Product {prod_id} references nonexistent category_id {cat_id}"
                )

            self._products_by_barcode[barcode_clean] = prod

    def get_categories(self) -> List[Dict[str, Any]]:
        """Return all categories."""
        return [dict(cat) for cat in self._categories]

    def get_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve category details by numeric ID."""
        cat = self._categories_by_id.get(category_id)
        return dict(cat) if cat else None

    def _resolve_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attach dynamically resolved category name to product dictionary."""
        resolved = dict(product_data)
        category = self.get_category_by_id(product_data.get("category_id", -1))
        resolved["category_name"] = (
            category["name"] if category else "Unknown Category"
        )
        if category and "code" in category:
            resolved["category_code"] = category["code"]
        return resolved

    def get_products(self, resolve_categories: bool = True) -> List[Dict[str, Any]]:
        """Return all products in catalogue, resolving categories by default."""
        if resolve_categories:
            return [self._resolve_product(p) for p in self._products]
        return [dict(p) for p in self._products]

    def lookup_by_barcode(self, barcode: str) -> Dict[str, Any]:
        """
        Lookup a product by its exact barcode string.

        Args:
            barcode: Barcode string to search.

        Returns:
            Resolved product dictionary including category information.

        Raises:
            InvalidBarcodeError: If barcode is empty, whitespace, or malformed.
            ProductNotFoundError: If no product matches the barcode.
        """
        if barcode is None or not isinstance(barcode, str):
            raise InvalidBarcodeError("Barcode must be a non-empty string.")

        clean_barcode = barcode.strip()
        if not clean_barcode:
            raise InvalidBarcodeError("Barcode cannot be empty or whitespace.")

        product = self._products_by_barcode.get(clean_barcode)
        if not product:
            raise ProductNotFoundError(f"Product not found for barcode: '{clean_barcode}'")

        return self._resolve_product(product)

    def get_category_summary(self) -> List[Dict[str, Any]]:
        """Return categories with their associated product counts."""
        counts: Dict[int, int] = {cat["id"]: 0 for cat in self._categories}
        for prod in self._products:
            cid = prod.get("category_id")
            if cid in counts:
                counts[cid] += 1

        summary = []
        for cat in self._categories:
            item = dict(cat)
            item["product_count"] = counts.get(cat["id"], 0)
            summary.append(item)
        return summary


# Global default instance for application use
default_catalogue = Catalogue()
