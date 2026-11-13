"""
Unit tests for the Catalogue and data integrity logic.
"""

from pathlib import Path
import pytest

from app.catalogue import (
    Catalogue,
    InvalidBarcodeError,
    ProductNotFoundError,
    default_catalogue,
)


def test_catalogue_initialization_and_counts():
    """Verify default catalogue loads all 8 categories and 16 products."""
    categories = default_catalogue.get_categories()
    products = default_catalogue.get_products()

    assert len(categories) == 8
    assert len(products) == 16


def test_unique_barcodes_in_catalogue():
    """Verify that every barcode across the catalogue is unique."""
    products = default_catalogue.get_products(resolve_categories=False)
    barcodes = [p["barcode"] for p in products]

    assert len(barcodes) == len(set(barcodes)), "Duplicate barcodes found in catalogue!"


def test_unique_product_ids_in_catalogue():
    """Verify that every product ID across the catalogue is unique."""
    products = default_catalogue.get_products(resolve_categories=False)
    product_ids = [p["id"] for p in products]

    assert len(product_ids) == len(set(product_ids)), "Duplicate product IDs found!"


def test_category_mapping_integrity():
    """Verify that every product's category_id points to an existing category."""
    categories = default_catalogue.get_categories()
    category_ids = {c["id"] for c in categories}
    products = default_catalogue.get_products(resolve_categories=False)

    assert len(category_ids) == 8

    for p in products:
        assert (
            p["category_id"] in category_ids
        ), f"Product {p['id']} has orphaned category_id {p['category_id']}"


def test_successful_barcode_lookup():
    """Verify exact barcode matching and category name resolution."""
    # Test first demo product (Casual dress)
    res_1 = default_catalogue.lookup_by_barcode("BR000001")
    assert res_1["id"] == "PROD-001"
    assert res_1["barcode"] == "BR000001"
    assert res_1["category_id"] == 1
    assert res_1["category_name"] == "Dress — Casual"
    assert "DEMO" in res_1["name"]

    # Test Abaya category demo product
    res_2 = default_catalogue.lookup_by_barcode("BR000009")
    assert res_2["id"] == "PROD-009"
    assert res_2["barcode"] == "BR000009"
    assert res_2["category_id"] == 5
    assert res_2["category_name"] == "Abaya"

    # Test last demo product
    res_3 = default_catalogue.lookup_by_barcode("BR000016")
    assert res_3["id"] == "PROD-016"
    assert res_3["barcode"] == "BR000016"
    assert res_3["category_id"] == 8
    assert res_3["category_name"] == "Dress — Ready Wear"


def test_barcode_lookup_strips_whitespace():
    """Verify leading/trailing whitespace is handled during lookup."""
    res = default_catalogue.lookup_by_barcode("  BR000002  ")
    assert res["id"] == "PROD-002"
    assert res["barcode"] == "BR000002"
    assert res["category_name"] == "Dress — Casual"


def test_unknown_barcode_raises_not_found():
    """Verify searching for an unregistered barcode raises ProductNotFoundError."""
    with pytest.raises(ProductNotFoundError) as exc_info:
        default_catalogue.lookup_by_barcode("BR999999")
    assert "BR999999" in str(exc_info.value)


@pytest.mark.parametrize("invalid_barcode", ["", "   ", "\t\n", None])
def test_invalid_barcode_input_raises_error(invalid_barcode):
    """Verify empty, whitespace-only, or None barcodes raise InvalidBarcodeError."""
    with pytest.raises(InvalidBarcodeError):
        default_catalogue.lookup_by_barcode(invalid_barcode)


def test_category_summary_counts():
    """Verify category summary reports correct counts (2 products per category)."""
    summary = default_catalogue.get_category_summary()
    assert len(summary) == 8
    for cat in summary:
        assert cat["product_count"] == 2, f"Category {cat['name']} expected 2 demo products"


def test_catalogue_missing_files(tmp_path):
    """Verify catalogue handles missing data files gracefully with FileNotFoundError."""
    non_existent_cat = tmp_path / "missing_cat.json"
    non_existent_prod = tmp_path / "missing_prod.json"

    with pytest.raises(FileNotFoundError):
        Catalogue(categories_path=non_existent_cat, products_path=non_existent_prod)
