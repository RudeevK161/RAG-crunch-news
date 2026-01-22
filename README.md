# RAG-crunch-news
Данный репозиторий содержит код проект AG-crunch-news.

Задача: Построение системы для извлечения информации об айти трендах с использованием RAG.
Техническая суть:
- Retrieval (Поиск): BM25/sparse + dense эмбеддинги для нахождения релевантных статей
- Augmentation (Обогащение): Контекстуализация запроса найденными документами
- Generation (Генерация): LLM () формирует ответ на основе извлеченной информации


Baseline (что было реализовано):
- написан парсер, для парсинга статей с новостных лент
- размечен валидационный датасет для проверки различных encoder моделей
- получены sparse эмбединги (BM25)
- получены dense эмбединги (Qwen/Qwen3-Embedding-0.6B)
- опробованы различные модели из mteb/leaderboard для выявления наиболее подходящей под данные: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, Octen/Octen-Embedding-0.6B, Qwen/Qwen3-Embedding-0.6B)
- развернута векторная БД Qdrant и в нее положены эмбединги


Dataset:

- Датасет состоит из 5500 статей (постепенно будет увеличн до 10000), которые были получены парсингом с сайта .
[here](https://techcrunch.com)

Если нужны артефакты, то можно их скачать здесь.
[here](https://console.yandex.cloud/folders/b1gpjgkmbvf6erheh5a2/storage/buckets/rag-crunch-news?key=data%2F&versionsDisplay=false&versionsDisplay=false_link)
