from pathlib import Path
import os
from sentence_transformers import SentenceTransformer

from app.core.search_config import search_config
from app.core.generation_config import generation_config


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_model_ready(model_path: Path) -> bool:
    if not model_path.exists():
        return False
    try:
        files = list(model_path.iterdir())
        if not files:
            return False
    except:
        return False
    return True


def preload_model(model_name: str, model_type: str) -> None:
    print(f"[bootstrap] Loading {model_type} model: {model_name}")
    model = SentenceTransformer(model_name)
    test_embedding = model.encode("test")
    print(f"[bootstrap] {model_type} model ready")


def main() -> None:
    os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '600'
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

    preload_model(generation_config.SEM_MODEL_NAME, "Semantic")
    preload_model(search_config.EMBEDDING_MODEL, "Embedding")

    print("[bootstrap] All models are ready.")


if __name__ == "__main__":
    main()