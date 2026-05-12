# RAG-crunch-news

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.13-red.svg)](https://qdrant.tech/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-orange.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)

Система интеллектуального поиска и анализа технологических новостей на основе архитектуры **Retrieval-Augmented Generation (RAG)**.

Проект предназначен для ответа на сложные пользовательские вопросы по материалам [TechCrunch](https://techcrunch.com) с использованием семантического поиска по векторной базе данных и генерации ответов на основе извлечённого контекста.

---

## 🎯 Основные возможности

- Семантический поиск по статьям TechCrunch
- Генерация ответов с использованием больших языковых моделей (LLM)
- Векторное хранилище на базе Qdrant
- Telegram-бот для взаимодействия с пользователем
- Административная панель на Streamlit
- Асинхронная обработка задач через Celery
- Кэширование результатов в Redis
- Автоматическая индексация новых статей

---

## 📊 Результаты экспериментальной оценки

Качество системы оценивалось по пяти метрикам:

- релевантность;
- точность;
- полнота;
- лаконичность;
- обоснованность.

| Категория | Доля ответов |
|----------|-------------:|
| Excellent | 62.3% |
| Good | 22.1% |
| Fair | 9.1% |
| Poor | 6.5% |

> **84.4% ответов получили высокую оценку (Excellent + Good).**

---

## 🏗️ Архитектура системы

```text
Client Layer
├── Telegram Bot
└── Streamlit Admin Panel
        │
        ▼
      Nginx
        │
        ▼
     FastAPI API
        │
 ┌──────┼───────────────┐
 ▼      ▼               ▼
Qdrant Redis          Celery

## 🛠️ Технологический стек

| Компонент | Технология | Назначение |
|----------|------------|------------|
| Backend API | FastAPI | REST API для обработки пользовательских запросов |
| Векторная база данных | Qdrant | Хранение эмбеддингов и семантический поиск документов |
| Генеративная модель | Qwen3-4B / Qwen2.5-7B | Генерация ответов на основе извлечённого контекста |
| Модель эмбеддингов | Octen-Embedding-0.6B | Преобразование текстов в векторные представления |
| Очередь задач | Celery | Асинхронное выполнение длительных операций |
| Брокер сообщений и кэш | Redis | Хранение промежуточных результатов и обмен сообщениями |
| Web-интерфейс | Streamlit | Административная панель |
| Telegram-интерфейс | python-telegram-bot | Пользовательский интерфейс в Telegram |
| Reverse Proxy | Nginx | Маршрутизация HTTP-запросов |
| Контейнеризация | Docker Compose | Оркестрация сервисов |

---

## 📁 Структура проекта

```text
RAG-crunch-news/
├── app/
│   ├── api/                    # REST API, роутеры и схемы
│   │   ├── routers/
│   │   └── schemas/
│   ├── core/                   # Конфигурация приложения
│   ├── services/
│   │   ├── generator/          # Генерация ответов
│   │   └── retrieval/          # Поиск и ранжирование документов
│   ├── tasks/                  # Celery-задачи
│   └── techcrunch_parser/      # Парсер и индексация статей TechCrunch
│
├── admin_panel/                # Streamlit-панель администратора
│   └── app.py
│
├── telegram_bot/               # Telegram-бот
│   └── bot.py
│
├── src/
│   ├── preload_models.py       # Предварительная загрузка моделей
│   └── setup_qdrant.py         # Создание коллекции Qdrant
│
├── data/                       # Датасеты и тестовые вопросы
├── notebooks/                  # Jupyter-ноутбуки
├── static/                     # Статические ресурсы
│
├── main.py                     # Точка входа FastAPI
├── Dockerfile                  # Docker-образ приложения
├── docker-compose.yaml         # Конфигурация сервисов
├── nginx.conf                  # Настройки Nginx
├── requirements.txt           # Python-зависимости
└── README.md
```

> Служебные директории (`venv/`, `models_cache/`, `__pycache__/`, `.idea/`) не включены в структуру проекта.

---

## 📦 Датасет

В качестве корпуса документов используются статьи технологического издания [TechCrunch](https://techcrunch.com).

Характеристики датасета:

- **Количество статей:** 5 488
- **Тематика:** искусственный интеллект, стартапы, инвестиции, венчурный рынок и технологические тренды
- **Формат хранения:** JSON
- **Валидационная выборка:** 100 размеченных пользовательских запросов и эталонных ответов

Пример файла корпуса:

```text
data/techcrunch_ai_5488_articles_20260112_1535.json
```

Пример файла с тестовыми вопросами:

```text
data/questions.json
```

---

## 🚀 Быстрый старт

### Предварительные требования

Перед запуском убедитесь, что установлены:

- Docker
- Docker Compose
- Не менее 8 ГБ оперативной памяти
- API-ключ для используемой языковой модели (при необходимости)

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/RAG-crunch-news.git
cd RAG-crunch-news
```

### 2. Создание файла `.env`

```bash
cp .env.example .env
```

Заполните необходимые переменные окружения:

- `BOT_TOKEN`
- `OPENAI_API_KEY` (или другой API-ключ)
- параметры подключения к Redis и Qdrant

### 3. Сборка Docker-образов

```bash
docker compose build
```

### 4. Предварительная загрузка моделей

Команда скачивает модели эмбеддингов и генерации в каталог `models_cache/`.

```bash
docker compose run --rm model_init
```

### 5. Запуск сервисов

```bash
docker compose up -d
```

### 6. Инициализация коллекции Qdrant

```bash
docker compose exec api python src/setup_qdrant.py
```

### 7. Индексация статей TechCrunch

```bash
docker compose exec api python -m app.techcrunch_parser.main
```

### 8. Проверка работы API

Откройте документацию Swagger:

```text
http://localhost:8000/docs
```

---

## 🌐 Доступные сервисы

После запуска будут доступны следующие сервисы:

| Сервис | URL | Назначение |
|------|-----|------------|
| FastAPI | http://localhost:8000 | Основной REST API |
| Swagger UI | http://localhost:8000/docs | Интерактивная документация API |
| Streamlit Admin Panel | http://localhost:8501 | Административная панель |
| Qdrant Dashboard | http://localhost:6333/dashboard | Просмотр коллекций и векторов |
| Nginx Gateway | http://localhost | Единая точка входа |

---

## 🤖 Telegram Bot

После запуска всех сервисов Telegram-бот автоматически становится доступным пользователям, если в файле `.env` указан корректный `BOT_TOKEN`.

---

## 🧪 Пример API-запроса

```bash
curl -X POST "http://localhost:8000/rag/ask" \
  -H "Content-Type: application/json" \
  -d '{
        "question": "Какие стартапы в сфере AI получили финансирование в январе 2026 года?"
      }'
```
