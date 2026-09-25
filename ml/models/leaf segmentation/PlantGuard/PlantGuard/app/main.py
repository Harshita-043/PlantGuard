
# app/main.py

import os
import uuid
import shutil

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)

from .inference import PlantGuard


app = FastAPI(
    title="PlantGuard",
    version="1.0.0",
    description="Leaf segmentation using fine-tuned SAM 2"
)


# Load model once when application starts
plantguard = PlantGuard()


@app.get("/")
def root():

    return {
        "application": "PlantGuard",
        "status": "running"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


@app.post("/predict")
async def predict(
    file: UploadFile = File(...)
):

    if not file.content_type.startswith(
        "image/"
    ):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image."
        )

    temp_path = (
        f"/tmp/"
        f"{uuid.uuid4().hex}_"
        f"{file.filename}"
    )

    try:

        with open(
            temp_path,
            "wb"
        ) as f:

            shutil.copyfileobj(
                file.file,
                f
            )

        result = plantguard.predict(
            temp_path,
            save_results=True
        )

        return {
            "status": "success",
            "leaf_count": result["count"],
            "metadata": result.get(
                "metadata",
                []
            )
        }

    finally:

        if os.path.exists(
            temp_path
        ):

            os.remove(
                temp_path
            )