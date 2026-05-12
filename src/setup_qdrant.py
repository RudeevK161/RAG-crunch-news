import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct
import joblib


def upload_pickle_to_qdrant(
        pickle_path: str,
        collection: str,
        vector_size: int,
        distance: str,
        batch_size: int,
        qdrant_host: str,
        qdrant_port: int,
        force_recreate: bool
):
    import logging
    logger = logging.getLogger(__name__)

    distance_map = {
        "Cosine": Distance.COSINE,
        "Euclidean": Distance.EUCLID,
        "Dot": Distance.DOT
    }

    import sys
    if not hasattr(np, '_core'):
        np._core = np.core
        sys.modules['numpy._core'] = np.core

    logger.info(f"Loading pickle file: {pickle_path}")
    logger.info(f"joblib")
    data = joblib.load(pickle_path)

    chunks = data.get('chunks', [])
    embeddings = data.get('embeddings', [])
    metadata_list = data.get('metadata', [])

    if not chunks or not embeddings:
        raise ValueError("Отсутствуют данные для загрузки")

    logger.info(f"Loaded {len(chunks)} chunks, {len(embeddings)} embeddings")

    client = QdrantClient(qdrant_host, port=qdrant_port)

    if force_recreate:
        try:
            client.delete_collection(collection)
            logger.info(f"Deleted collection {collection}")
        except:
            pass

    try:
        client.get_collection(collection)
        logger.info(f"Collection {collection} already exists")
    except:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance_map[distance]
            )
        )
        logger.info(f"Created collection {collection}")

    total_uploaded = 0
    for batch_start in range(0, len(chunks), batch_size):
        batch_end = min(batch_start + batch_size, len(chunks))
        points = []

        for i in range(batch_start, batch_end):
            chunk = chunks[i]
            embedding = embeddings[i]
            metadata = metadata_list[i] if i < len(metadata_list) else {}

            if hasattr(embedding, 'tolist'):
                vector = embedding.tolist()
            else:
                vector = embedding

            payload = {
                "text": chunk.get('text', ''),
                "original_text": chunk.get('original_text', ''),
                "chunk_id": chunk.get('chunk_id', f"chunk_{i}"),
                "document_id": chunk.get('document_id', ''),
                "chunk_index": chunk.get('chunk_index', i),
                "total_chunks": chunk.get('total_chunks', len(chunks)),
                "title": metadata.get('title', '')
            }

            points.append(PointStruct(id=i, vector=vector, payload=payload))

        client.upsert(collection_name=collection, points=points)
        total_uploaded += len(points)

        logger.info(f"Uploaded batch {batch_start // batch_size + 1}, total: {total_uploaded}")

        del points

    collection_info = client.get_collection(collection)

    logger.info(f"Upload complete: {total_uploaded} points")

    return {
        "points_uploaded": total_uploaded,
        "points_count": collection_info.points_count
    }