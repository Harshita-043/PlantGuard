
# app/config.py

from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = Path(
    os.getenv(
        "MODEL_PATH",
        BASE_DIR / "models" / "plantguard_sam2.pt"
    )
)

MODEL_CONFIG = Path(
    os.getenv(
        "MODEL_CONFIG",
        BASE_DIR / "configs" / "sam2.1_hiera_s.yaml"
    )
)

DEVICE = os.getenv(
    "DEVICE",
    "cuda"
)

MAX_IMAGE_SIDE = int(
    os.getenv(
        "MAX_IMAGE_SIDE",
        "1280"
    )
)

POINTS_PER_SIDE = int(
    os.getenv(
        "POINTS_PER_SIDE",
        "32"
    )
)

MAX_LEAVES = int(
    os.getenv(
        "MAX_LEAVES",
        "20"
    )

)

LEAF_THRESHOLD = float(
    os.getenv(
        "LEAF_THRESHOLD",
        "0.5"
    )
)

OUTPUT_DIR = Path(
    os.getenv(
        "OUTPUT_DIR",
        BASE_DIR / "outputs"
    )
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ========================================================== # CLIP # ========================================================== 
USE_CLIP = True 
CLIP_MODEL_NAME = "ViT-B-32" 
CLIP_MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "clip"
    / "open_clip_model.safetensors"
) 
CLIP_PROMPTS = [ # Leaf prompts MUST come first. 
"a photo of a green leaf", 
"a photo of a leaf of a houseplant", 
# Non-leaf prompts. 
"a photo of a plant stem", 
"a photo of a terracotta flower pot", 
"a photo of a wall", 
"a photo of the floor", 
"a photo of soil", 
"a photo of a shadow", 
"a photo of a tile or pavement", 
] 

CLIP_LEAF_PROMPT_COUNT = 2 
CLIP_BATCH_SIZE = 32