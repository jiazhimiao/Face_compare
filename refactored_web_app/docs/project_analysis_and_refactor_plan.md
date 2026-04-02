# Face Compare Project Analysis And Refactor Plan

## 1. Project Understanding

This project is a face comparison prototype based on InsightFace. Its current value is that it already forms a usable closed loop:

1. Detect whether an image contains a face.
2. Verify whether an ID-card portrait and a live face photo belong to the same person.
3. Check whether a face matches any image in a blacklist library.
4. Prepare evaluation data and run ROC analysis to derive threshold suggestions.
5. Output visual artifacts for manual review.

The original repository achieves these goals mainly through:

- `face_similarity.py`: offline batch processing, feature extraction, verification, blacklist checking, visualization.
- `face_api.py`: JSON-in / JSON-out interface wrapper.
- `prepare_data.py`: evaluation data preparation.
- `roc_analysis.py`: ROC analysis and threshold recommendation.

## 2. Current Architectural Assessment

### Strengths

- The business workflow is complete.
- InsightFace embeddings are already used as the core representation.
- There is basic feature caching.
- The project supports both business processing and threshold evaluation.

### Main Risks

- Duplicate logic exists across scripts, especially between offline and API flows.
- Configuration is scattered across files.
- Threshold configuration and ROC-derived thresholds are not unified.
- Negative-pair generation for ROC is simplistic.
- Cache refresh relies mostly on file-name changes rather than file content or metadata changes.
- Visualization and business logic are coupled too tightly.

## 3. Refactor Goals

The refactor should keep the original files untouched and build a parallel, cleaner implementation that is easier to maintain and demonstrate.

Target goals:

1. Extract reusable core modules.
2. Centralize configuration.
3. Standardize result structures.
4. Separate visualization from business logic.
5. Improve feature-cache validation.
6. Improve ROC negative-pair generation.
7. Add a functional web page to demonstrate the three core business features.

## 4. New Target Structure

```text
refactored_web_app/
├─ app.py
├─ config.py
├─ core/
│  ├─ __init__.py
│  ├─ model.py
│  ├─ schemas.py
│  ├─ features.py
│  ├─ service.py
│  └─ visualization.py
├─ docs/
│  └─ project_analysis_and_refactor_plan.md
├─ scripts/
│  ├─ prepare_data.py
│  ├─ run_batch.py
│  └─ run_roc.py
├─ static/
│  └─ style.css
├─ templates/
│  └─ index.html
└─ runtime/
   ├─ features/
   ├─ output/
   └─ uploads/
```

## 5. Module Responsibilities

### `config.py`

- Manage model parameters, thresholds, paths, cache settings, and app settings.

### `core/model.py`

- Initialize the InsightFace engine.
- Read images.
- Extract face embeddings and bounding boxes.

### `core/features.py`

- Load and save cached embeddings.
- Track file metadata such as file size and modified time.
- Rebuild cache when image sets change.

### `core/schemas.py`

- Provide standardized data structures for results.

### `core/service.py`

- Provide the main business functions:
  - face detection
  - identity verification
  - blacklist checking
  - folder scan and batch processing

### `core/visualization.py`

- Generate visual summaries independently of the core business flow.

### `scripts/prepare_data.py`

- Prepare same-person and different-person evaluation datasets.
- Use more explicit pairing logic and random-seed based selection.

### `scripts/run_roc.py`

- Build same-person and different-person pairs.
- Compute ROC / AUC.
- Output JSON summary for threshold recommendations.

### `app.py`

- Provide a Flask-based web app.
- Expose three functional endpoints.
- Serve a single demo web page.

## 6. Web Frontend Requirement

The refactor includes a functional web page to demonstrate the three core business capabilities:

1. Face detection
2. Identity verification
3. Blacklist matching

The page should:

- Provide upload forms for each function.
- Return structured results.
- Display success/failure state and confidence values.
- Keep the interaction simple enough for demo and manual verification.

## 7. Result Standardization

Suggested response structure:

```json
{
  "success": true,
  "message": "Operation completed",
  "data": {
    "function_name": "...",
    "result": {}
  }
}
```

For business-specific outputs:

- Face detection:
  - `has_face`
  - `bbox`
- Identity verification:
  - `verified`
  - `similarity`
  - `threshold`
- Blacklist match:
  - `matched`
  - `matched_name`
  - `similarity`
  - `threshold`

## 8. Refactor Execution Order

1. Create a parallel implementation directory.
2. Add the design-and-analysis MD document.
3. Extract reusable core modules.
4. Centralize configuration.
5. Standardize result data.
6. Separate visualization utilities.
7. Add batch and ROC scripts.
8. Build the web page for the three core features.
9. Verify backend functions.
10. Verify the web routes.

## 9. Validation Plan

Validation should confirm:

1. The new modules import successfully.
2. The model initializes successfully.
3. The three core functions run against sample images.
4. The Flask endpoints return valid JSON.
5. The original project files remain untouched.

## 10. Implementation Note

This refactor is intentionally additive. The original files are preserved as-is, and all new work is isolated in `refactored_web_app/`.
