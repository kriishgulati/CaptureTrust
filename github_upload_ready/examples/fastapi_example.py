"""Minimal FastAPI service that inspects an uploaded image.

Install the extras first:

    pip install fastapi uvicorn python-multipart

Run with:

    uvicorn examples.fastapi_example:app --reload

Then POST an image to /inspect as multipart form-data under the field "file".
Images are processed in-memory and never persisted by CaptureTrust.
"""

from __future__ import annotations

import numpy as np

try:
    import cv2
    from fastapi import FastAPI, File, HTTPException, UploadFile
except ImportError as exc:  # pragma: no cover - example-only dependency guard
    raise SystemExit(
        "This example needs fastapi, uvicorn, python-multipart and opencv. "
        "Install them with: pip install fastapi uvicorn python-multipart"
    ) from exc

from capturetrust import CaptureTrustError, inspect_array

app = FastAPI(title="CaptureTrust demo")


@app.post("/inspect")
async def inspect(file: UploadFile = File(...)) -> dict[str, object]:
    raw = await file.read()
    buffer = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")

    try:
        report = inspect_array(image)
    except CaptureTrustError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return report.to_dict()
