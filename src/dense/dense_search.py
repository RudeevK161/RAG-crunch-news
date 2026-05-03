import numpy as np
from typing import List
from datetime import datetime


def enhanced_dense_search(
        model,
        article_id_to_idx,
        article_embeddings_norm,
        title_embeddings_norm,
        query: str, k: int = 10,
        text_weight: float = 0.7,
        title_weight: float = 0.3) -> List[str]:
    """
    Улучшенный поиск с учетом текста и названий статей

    Args:
        model:
        article_id_to_idx:
        title_embeddings_norm:
        article_embeddings_norm:
        query: текст запроса
        k: количество результатов
        text_weight: вес текста статьи (0-1)
        title_weight: вес названия статьи (0-1)
    """

    query_emb = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    text_similarities = query_emb @ article_embeddings_norm.T

    title_similarities = query_emb @ title_embeddings_norm.T

    combined_scores = (text_weight * text_similarities +
                       title_weight * title_similarities)

    top_indices = np.argsort(-combined_scores)[:k]
    top_ids = []
    for idx in top_indices:
        for article_id, article_idx in article_id_to_idx.items():
            if article_idx == idx:
                top_ids.append(article_id)
                break

    return top_ids


def enhanced_time_dense_search(
        model,
        articles,
        article_id_to_idx,
        article_embeddings_norm,
        title_embeddings_norm,
        query: str,
        k: int = 10,
        text_weight: float = 0.6,
        title_weight: float = 0.2,
        recency_weight: float = 0.2,
        time_decay_days: int = 365
) -> List[str]:
    """
    Улучшенный поиск с учетом текста, названий и актуальности статей
    """

    query_emb = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    text_similarities = query_emb @ article_embeddings_norm.T

    title_similarities = query_emb @ title_embeddings_norm.T

    current_time = datetime.now()
    time_scores = []

    for article in articles:
        try:
            pub_time = datetime.fromisoformat(article.get('published_time', '2020-01-01'))
            days_diff = (current_time - pub_time).days
            time_score = np.exp(-days_diff / time_decay_days)
        except:
            time_score = 0.1

        time_scores.append(time_score)

    time_scores = np.array(time_scores)
    time_scores = time_scores / time_scores.max()

    combined_scores = (
            text_weight * text_similarities +
            title_weight * title_similarities +
            recency_weight * time_scores
    )

    top_indices = np.argsort(-combined_scores)[:k]

    top_ids = []
    for idx in top_indices:
        for article_id, article_idx in article_id_to_idx.items():
            if article_idx == idx:
                top_ids.append(article_id)
                break

    return top_ids


def basic_dense_search(model, article_id_to_idx, article_embeddings_norm, query: str, k: int = 10) -> List[str]:
    """Только по тексту статей"""

    query_emb = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    similarities = query_emb @ article_embeddings_norm.T
    top_indices = np.argsort(-similarities)[:k]

    top_ids = []
    for idx in top_indices:
        for article_id, article_idx in article_id_to_idx.items():
            if article_idx == idx:
                top_ids.append(article_id)
                break

    return top_ids


def evaluate_search(questions, search_func, k_values=[1, 3, 5, 10]):
    """Оценка поиска с выводом метрик и деталей"""
    print(f"\n{'=' * 60}")
    print("ОЦЕНКА ПОИСКА ПО DENSE ЭМБЕДДИНГАМ")
    print(f"{'=' * 60}")

    results = []

    for k in k_values:
        print(f"\nТОП-{k} РЕЗУЛЬТАТЫ:")
        print("-" * 80)

        total_precision = 0
        total_recall = 0
        total_hit = 0
        total_mrr = 0
        valid_queries = 0

        for i, question_data in enumerate(questions):
            query = question_data.get("question", "")
            correct_ids = set(question_data.get("id", []))

            if not correct_ids:
                continue

            found_ids = search_func(query, k=k)

            correct_found = [id for id in found_ids if id in correct_ids]

            # Precision@K
            precision = len(correct_found) / k if k > 0 else 0

            # Recall@K
            recall = len(correct_found) / len(correct_ids) if correct_ids else 0

            # Hit Rate@K
            hit = 1 if len(correct_found) > 0 else 0

            # MRR@K
            mrr = 0
            for rank, found_id in enumerate(found_ids, 1):
                if found_id in correct_ids:
                    mrr = 1.0 / rank
                    break

            total_precision += precision
            total_recall += recall
            total_hit += hit
            total_mrr += mrr
            valid_queries += 1

            if i < 3:
                print(f"\nВопрос {i + 1}: '{query[:50]}...'")
                print(f"Правильные ID: {list(correct_ids)}")
                print(f"Найденные ID: {found_ids}")
                print(f"Совпадения: {correct_found}")
                print(f"Несовпадения: {[id for id in found_ids if id not in correct_ids]}")
                print(f"Precision@{k}: {precision:.3f}, Recall@{k}: {recall:.3f}")

        if valid_queries > 0:
            avg_precision = total_precision / valid_queries
            avg_recall = total_recall / valid_queries
            avg_hit = total_hit / valid_queries
            avg_mrr = total_mrr / valid_queries

            # F1-score
            f1 = 2 * avg_precision * avg_recall / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0

            print(f"\n{'=' * 80}")
            print(f"ИТОГО ДЛЯ TOP-{k} (на {valid_queries} вопросах):")
            print(f"  Precision@{k}: {avg_precision:.3f}")
            print(f"  Recall@{k}:    {avg_recall:.3f}")
            print(f"  F1@{k}:        {f1:.3f}")
            print(f"  Hit Rate@{k}:  {avg_hit:.3f}")
            print(f"  MRR@{k}:       {avg_mrr:.3f}")
            print(f"{'=' * 80}")

            results.append({
                'k': k,
                'precision': avg_precision,
                'recall': avg_recall,
                'f1': f1,
                'hit_rate': avg_hit,
                'mrr': avg_mrr
            })

    return results