# EAN-13 Damaged Barcode Evaluation Dataset

This dataset evaluates the research question:
> "For EAN-13 barcodes damaged by fading, scratches, smudges, low contrast, or skew, can a structure-aware recovery pipeline improve exact product-code recovery over a standard decoder without increasing false product identifications?"

## Provenance & Ground Truth Pairings

- **Total Test Cases:** 42
- **Ground Truth GTINs:** 6 distinct valid EAN-13 codes
- **Synthetic Status:** Clearly marked with `synthetic: true`. Artificially degraded images are used for controlled ablation and must not be conflated with real-world empirical distributions.

## Damage Categories
1. **clean**: Reference baseline controls.
2. **fading**: Low intensity contrast between bars and substrate.
3. **scratches**: Surface cuts obliterating portions of scanlines.
4. **smudges**: Localized ink bleeds obscuring guards and module transitions.
5. **low_contrast**: Heavily compressed dynamic range (15 discrete intensity levels).
6. **skew**: 25° rotational misalignment exceeding standard 1D linear rasterization.
7. **severe_unrecoverable**: Unrecoverable noise control verifying that the pipeline safely abstains rather than making false identifications.

## Instructions for Adding Real Captured Barcode Images

To extend this benchmark with real-world captured images:
1. Place the captured image in the `images/` directory (e.g. `images/real_photo_01.jpg`).
2. Pair it with its known, independently verified ground truth GTIN.
3. Add an entry to `manifest.json`:
   ```json
   {
     "filename": "real_photo_01.jpg",
     "relative_path": "images/real_photo_01.jpg",
     "ground_truth_code": "4006381333931",
     "damage_type": "real_world_glare",
     "synthetic": false,
     "provenance": "Captured via mobile camera under fluorescent lighting",
     "description": "Packaging fold with specular reflection"
   }
   ```
4. Re-run `python scripts/evaluate_recovery.py` to evaluate both decoders against the updated corpus.
