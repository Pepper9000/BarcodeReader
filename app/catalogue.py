
"""
Catalogue management module for BarcodeReader.

Handles loading, validating, resolving, and querying categories and products
from JSON data storage.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional


class CatalogueError(Exception):
    """Base exception for catalogue operations."""


class ProductNotFoundError(CatalogueError):
    """Raised when a barcode cannot be matched to any product."""


class InvalidBarcodeError(CatalogueError):
    """Raised when barcode input is empty or malformed."""


class DuplicateBarcodeError(CatalogueError):
    """Raised when attempting to add a product with a barcode that already exists."""


class InvalidProductError(CatalogueError):
    """Raised when product attributes are missing, empty, or invalid."""


class Catalogue:
    """Manages product and category catalogues loaded from JSON."""

    def __init__(
        self,
        categories_path: Optional[Path | str] = None,
        products_path: Optional[Path | str] = None,
        data_dir: Optional[Path | str] = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent
        seed_data_dir = base_dir / "data"

        # Determine target data directory (argument -> env vars -> bundled data directory)
        env_dir = os.environ.get("DATA_DIR") or os.environ.get("CATALOGUE_DATA_DIR")
        target_dir = (
            Path(data_dir)
            if data_dir
            else (Path(env_dir) if env_dir else seed_data_dir)
        )

        # If an external/persistent directory is configured, ensure it exists and preserve
        # the initial seed catalogue files if not already present on first startup.
        if target_dir.resolve() != seed_data_dir.resolve():
            target_dir.mkdir(parents=True, exist_ok=True)
            target_prod = target_dir / "products.json"
            target_cat = target_dir / "categories.json"
            seed_prod = seed_data_dir / "products.json"
            seed_cat = seed_data_dir / "categories.json"

            if not target_prod.exists() and seed_prod.exists():
                shutil.copy2(seed_prod, target_prod)
            if not target_cat.exists() and seed_cat.exists():
                shutil.copy2(seed_cat, target_cat)

        self.categories_path = (
            Path(categories_path)
            if categories_path
            else target_dir / "categories.json"
        )

        self.products_path = (
            Path(products_path)
            if products_path
            else target_dir / "products.json"
        )

        self._categories: List[Dict[str, Any]] = []
        self._products: List[Dict[str, Any]] = []
        self._categories_by_id: Dict[int, Dict[str, Any]] = {}
        self._products_by_barcode: Dict[str, Dict[str, Any]] = {}

        self.reload()

    def reload(self) -> None:
        """Reload catalogue files and validate their contents."""
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
        """Validate products and register their barcode identifiers."""

        self._categories_by_id = {}

        for cat in self._categories:
            cat_id = cat.get("id")

            if cat_id is None:
                raise ValueError(f"Category missing ID: {cat}")

            if cat_id in self._categories_by_id:
                raise ValueError(f"Duplicate category ID: {cat_id}")

            self._categories_by_id[cat_id] = cat

        self._products_by_barcode = {}
        seen_product_ids = set()

        structured_prefixes = {
            1: "DR-CA",
            2: "DR-PA",
            3: "KU-CO",
            4: "HI",
            5: "AB",
            6: "RL-BL",
            7: "DR-DM",
            8: "DR-RW",
        }

        category_counters = {}

        for prod in self._products:
            prod_id = prod.get("id")
            barcode = prod.get("barcode")
            cat_id = prod.get("category_id")

            if not prod_id:
                raise ValueError(f"Product missing ID: {prod}")

            if prod_id in seen_product_ids:
                raise ValueError(f"Duplicate product ID: {prod_id}")

            seen_product_ids.add(prod_id)

            if not isinstance(barcode, str) or not barcode.strip():
                raise ValueError(f"Invalid barcode: {prod}")

            barcode_clean = barcode.strip()

            if barcode_clean in self._products_by_barcode:
                raise ValueError(
                    f"Duplicate barcode: {barcode_clean}"
                )

            if cat_id not in self._categories_by_id:
                raise ValueError(
                    f"Product {prod_id} references invalid category {cat_id}"
                )

            # Register existing barcode
            self._products_by_barcode[barcode_clean] = prod

            # Generate structured barcode alias
            prefix = structured_prefixes.get(cat_id)

            if prefix:
                category_counters[cat_id] = (
                    category_counters.get(cat_id, 0) + 1
                )

                item_number = category_counters[cat_id]

                structured_barcode = (
                    f"{prefix}-{item_number:03d}"
                )

                if structured_barcode in self._products_by_barcode:
                    raise ValueError(
                        f"Duplicate structured barcode: {structured_barcode}"
                    )

                self._products_by_barcode[structured_barcode] = prod

    def get_categories(self) -> List[Dict[str, Any]]:
        """Return all categories."""
        return [dict(cat) for cat in self._categories]

    def get_category_by_id(
        self, category_id: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieve category details."""
        cat = self._categories_by_id.get(category_id)
        return dict(cat) if cat else None

    def _resolve_product(
        self, product_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attach category information to a product."""

        resolved = dict(product_data)
        
        for code, prod in self._products_by_barcode.items():
            if prod["id"] == product_data["id"] and not code.startswith("BR"):
                resolved["structured_barcode"] = code
                break

        category = self.get_category_by_id(
            product_data.get("category_id", -1)
        )

        resolved["category_name"] = (
            category["name"] if category else "Unknown Category"
        )

        if category and "code" in category:
            resolved["category_code"] = category["code"]

        return resolved

    def get_products(
        self, resolve_categories: bool = True
    ) -> List[Dict[str, Any]]:
        """Return all products."""

        if resolve_categories:
            return [
                self._resolve_product(p)
                for p in self._products
            ]

        return [dict(p) for p in self._products]

    def lookup_by_barcode(
        self, barcode: str
    ) -> Dict[str, Any]:
        """Find a product using either barcode format."""

        if barcode is None or not isinstance(barcode, str):
            raise InvalidBarcodeError(
                "Barcode must be a non-empty string."
            )

        clean_barcode = barcode.strip()

        if not clean_barcode:
            raise InvalidBarcodeError(
                "Barcode cannot be empty or whitespace."
            )

        product = self._products_by_barcode.get(clean_barcode)

        if not product:
            raise ProductNotFoundError(
                f"Product not found for barcode: '{clean_barcode}'"
            )

        return self._resolve_product(product)

    def get_category_summary(self) -> List[Dict[str, Any]]:
        """Return categories with product counts."""

        counts: Dict[int, int] = {
            cat["id"]: 0 for cat in self._categories
        }

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

    def add_product(
        self,
        barcode: str,
        name: str,
        category_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Add a new product to the catalogue and persist it to JSON storage.

        Args:
            barcode: Barcode identifier (required, non-empty, unique).
            name: Product name (required, non-empty).
            category_id: Category ID (optional; defaults to 1).

        Returns:
            The resolved product dictionary.

        Raises:
            InvalidProductError: If name or barcode is empty or malformed.
            DuplicateBarcodeError: If barcode already exists in the catalogue.
        """
        if barcode is None or not isinstance(barcode, str):
            raise InvalidProductError("Barcode must be a non-empty string.")
        clean_barcode = barcode.strip()
        if not clean_barcode:
            raise InvalidProductError("Barcode cannot be empty or whitespace.")

        if name is None or not isinstance(name, str):
            raise InvalidProductError("Product name must be a non-empty string.")
        clean_name = name.strip()
        if not clean_name:
            raise InvalidProductError("Product name cannot be empty or whitespace.")

        # Check for duplicate barcode
        if clean_barcode in self._products_by_barcode:
            raise DuplicateBarcodeError(
                f"Product with barcode '{clean_barcode}' already exists in catalogue."
            )

        # Default category
        if category_id is None or category_id not in self._categories_by_id:
            cat_id = 1
        else:
            cat_id = category_id

        # Generate unique product ID: PROD-xxx
        max_num = 0
        for p in self._products:
            pid = str(p.get("id", ""))
            if pid.startswith("PROD-"):
                num_part = pid[5:]
                if num_part.isdigit():
                    max_num = max(max_num, int(num_part))
        new_id = f"PROD-{max_num + 1:03d}"

        new_prod = {
            "id": new_id,
            "barcode": clean_barcode,
            "name": clean_name,
            "category_id": cat_id,
        }

        self._products.append(new_prod)

        # Persist to disk using project storage approach
        with open(self.products_path, "w", encoding="utf-8") as f:
            json.dump(self._products, f, indent=2)

        # Re-index
        self._index_and_validate()

        return self._resolve_product(new_prod)

    def remove_product(self, barcode: str) -> bool:
        """Remove a product by barcode (primarily for testing and cleanup)."""
        if not isinstance(barcode, str):
            return False
        clean = barcode.strip()
        orig_len = len(self._products)
        self._products = [
            p for p in self._products if p.get("barcode", "").strip() != clean
        ]
        if len(self._products) != orig_len:
            with open(self.products_path, "w", encoding="utf-8") as f:
                json.dump(self._products, f, indent=2)
            self._index_and_validate()
            return True
        return False


# Global default instance
default_catalogue = Catalogue()
