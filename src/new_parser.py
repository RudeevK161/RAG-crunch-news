import requests
import json
import hashlib
from datetime import datetime, timedelta, date
import time
import random
from bs4 import BeautifulSoup
import re
import uuid


def parse_techcrunch_pagination(target_articles, max_pages):
    """Парсит статьи с пагинированных страниц TechCrunch AI"""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
    }

    session = requests.Session()
    session.headers.update(headers)

    all_articles = {}
    page = 1

    six_months_ago = datetime.now() - timedelta(days=180)

    print(f"Начинаю парсинг пагинации TechCrunch AI...")
    print(f"Цель: {target_articles} статей за последние 6 месяцев")
    print("=" * 60)

    while len(all_articles) < target_articles and page <= max_pages:
        # Формируем URL страницы
        if page == 1:
            url = "https://techcrunch.com/category/artificial-intelligence/"
        else:
            url = f"https://techcrunch.com/category/artificial-intelligence/page/{page}/"

        print(f"Страница {page}: {url}")

        try:
            # Загружаем страницу с случайной задержкой
            time.sleep(random.uniform(2, 4))

            response = session.get(url, timeout=15)

            if response.status_code == 404:
                print(f"  Страница {page} не найдена (404). Прекращаю парсинг.")
                break

            if response.status_code != 200:
                print(f"  Ошибка {response.status_code}. Пропускаю страницу.")
                page += 1
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # 🔧 ИСПРАВЛЕННЫЙ СЕЛЕКТОР: Находим ВСЕ статьи на странице
            # Используем правильные классы из HTML структуры TechCrunch
            article_elements = soup.find_all('li', class_='wp-block-post')

            if not article_elements:
                # Альтернативный селектор
                article_elements = soup.select('article.post-block, .post-block')

            if not article_elements:
                print(f"На странице {page} не найдены статьи. Пробую другой селектор...")
                # Еще один вариант поиска
                article_elements = soup.select('[class*="post-"]')

            if not article_elements or len(article_elements) == 0:
                print(f"На странице {page} статьи не найдены. Проверяю HTML...")
                # Выводим отладку для проверки структуры
                # print(soup.prettify()[:2000])  # Раскомментируйте для отладки
                break

            print(f"  Найдено статей: {len(article_elements)}")

            # Парсим каждую статью на странице
            articles_on_page = 0
            published_date = None

            for article_element in article_elements:
                try:
                    # 1. Извлекаем ссылку на статью - ИСПРАВЛЕННЫЙ СЕЛЕКТОР
                    link_element = article_element.select_one('a.loop-card__title-link')

                    # Если не нашли через класс, ищем по атрибуту data-destinationlink
                    if not link_element:
                        link_element = article_element.select_one('a[data-destinationlink]')

                    # Если все еще не нашли, ищем любую ссылку внутри
                    if not link_element:
                        link_element = article_element.select_one('a[href*="/202"]')

                    if not link_element:
                        print(f"    Не найдена ссылка в статье")
                        continue

                    article_url = link_element.get('href', '')
                    if not article_url:
                        # Пробуем получить из data-destinationlink
                        article_url = link_element.get('data-destinationlink', '')

                    if not article_url:
                        continue

                    if not article_url.startswith('http'):
                        article_url = 'https://techcrunch.com' + article_url

                    # 2. Извлекаем заголовок - ИСПРАВЛЕННЫЙ СЕЛЕКТОР
                    title_element = article_element.select_one('.loop-card__title')
                    if not title_element:
                        title_element = link_element

                    article_title = title_element.get_text(strip=True) if title_element else ""
                    """
                    
                    # 3. Извлекаем дату - ИСПРАВЛЕННЫЙ СЕЛЕКТОР
                    date_element = article_element.find('time', recursive=True)

                    print(f" Date {date_element}")
                    if date_element:
                        datetime_str = date_element.get('datetime')

                        if datetime_str:
                            date_str = datetime_str[:10]

                            try:
                                published_date = date.fromisoformat(date_str)
                                six_months_ago_date = six_months_ago.date()

                                if published_date < six_months_ago_date:
                                    print(f"    Статья слишком старая: {published_date}")
                                    continue
                            except Exception as e:
                                print(f"    Ошибка сравнения дат: {e}")
                    else:
                        published_date = date.today()
                    """

                    date_from_url = article_url.split('/')[3:6]
                    if date_from_url[0][:2]=='20':
                        published_date = '-'.join(date_from_url)


                    # 5. Получаем полный текст статьи (позже)
                    print(f"    Найдена статья: {article_title[:70]}...")

                    # 7. Создаем ID
                    article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, article_url))
                    #article_id = len(all_articles) + 1

                    # 8. Добавляем статью (пока без текста)
                    if article_url not in all_articles:
                        all_articles[article_url] = {
                            "id": article_id,
                            "title": article_title,
                            "url": article_url,
                            "published_time": published_date,
                        }

                        articles_on_page += 1
                        print(f"    ✓ Добавлена: {article_title[:60]}...")

                except Exception as e:
                    print(f"    Ошибка обработки статьи: {e}")
                    continue

            print(f"  На странице {page} добавлено статей: {articles_on_page}")
            print(f"  Всего собрано: {len(all_articles)}/{target_articles}")
            print(f"  Прогресс: {len(all_articles) / target_articles * 100:.1f}%")

            # Проверяем, есть ли следующая страница - ИСПРАВЛЕННЫЙ СЕЛЕКТОР
            next_page_link = soup.select_one('.wp-block-query-pagination-next, a[rel="next"]')
            if not next_page_link and len(article_elements) < 10:
                print("  Нет следующей страницы или мало статей. Прекращаю.")
                break

            page += 1

            print()  # Пустая строка для читаемости

        except requests.exceptions.Timeout:
            print(f"  Таймаут на странице {page}. Пропускаю.")
            page += 1
            continue
        except Exception as e:
            print(f"  Критическая ошибка на странице {page}: {e}")
            break

    # 🔧 ДОБАВЛЯЕМ ПОЛУЧЕНИЕ ПОЛНОГО ТЕКСТА ДЛЯ ВСЕХ СОБРАННЫХ СТАТЕЙ
    print(f"\nНачинаю получение полного текста для {len(all_articles)} статей...")

    articles_with_text = []
    processed_count = 0

    for i, (article_url, article_data) in enumerate(list(all_articles.items()), 1):
        try:
            total_articles = len(all_articles)
            print(f"[{i}/{total_articles}] Получаю текст: {article_data['title'][:60]}...")

            # Получаем полный текст
            full_text = extract_full_article_text(session, article_url)

            if not full_text or len(full_text) < 500:
                print(f"Текст слишком короткий или не найден")
                # Удаляем статью без текста
                del all_articles[article_url]
                continue

            # Проверяем, что это AI статья
           # if not is_ai_article(article_data['title'], full_text):
           #     print(f"Пропускаю (не AI тема)")
           #     # Удаляем не-AI статью
           #     del all_articles[article_url]
           #     continue

            # Добавляем текст к данным статьи
            article_data["text"] = full_text
            article_data["word_count"] = len(full_text.split())

            articles_with_text.append(article_data)
            processed_count += 1

            print(f"    ✓ Текст получен: {article_data['word_count']} слов")

            # Задержка между запросами статей
            time.sleep(random.uniform(0.5, 1.5))

        except Exception as e:
            print(f" Ошибка получения текста: {e}")
            # Удаляем проблемную статью
            if article_url in all_articles:
                del all_articles[article_url]
            continue

    # Конвертируем словарь в список и сортируем по дате
    articles_list = list(all_articles.values())
    #articles_list.sort(key=lambda x: x['published_time'], reverse=True)

    print("\n" + "=" * 60)
    print(f"ПАРСИНГ ЗАВЕРШЕН!")
    print(f"Всего собрано ссылок: {len(articles_list)}")
    print(f"Статей с текстом: {len(articles_with_text)}")
    print("=" * 60)

    return articles_list[:target_articles]


def extract_full_article_text(session, url):
    """Извлекает полный текст статьи"""
    try:
        time.sleep(random.uniform(0.5, 0.8))  # Задержка между запросами

        response = session.get(url, timeout=15)

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Удаляем ненужные элементы
        for element in soup.select('script, style, iframe, nav, footer, .advertisement, .share-buttons, .comments'):
            element.decompose()

        # Пробуем разные селекторы для основного контента
        content_selectors = [
            '.article-content',
            '.entry-content',
            '.single-post-content',
            'article .content',
            '.article__content',
            '.article-body',
            '.post-content',
            'article > div',
            '[class*="content"]',
            '.rich-text'
        ]


        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                # Извлекаем все текстовые элементы
                text_elements = content_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                text_parts = []

                for element in text_elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 30:  # Игнорируем короткие элементы
                        text_parts.append(text)

                if text_parts:
                    full_text = '\n\n'.join(text_parts)
                    if len(full_text) > 300:
                        return full_text

        # Резервный метод: все параграфы в статье
        article_tag = soup.find('article')
        if article_tag:
            paragraphs = article_tag.find_all('p')
            if paragraphs:
                text_parts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
                if text_parts:
                    full_text = '\n\n'.join(text_parts)
                    if len(full_text) > 300:
                        return full_text

        return None

    except Exception as e:
        print(f"      Ошибка получения текста: {e}")
        return None


def is_ai_article(title, text):
    """Проверяет, относится ли статья к AI тематике"""
    content = (title + ' ' + text).lower()

    # Ключевые слова AI
    ai_keywords = [
        'ai', 'artificial intelligence', 'machine learning', 'deep learning',
        'neural network', 'llm', 'gpt', 'chatgpt', 'generative ai',
        'computer vision', 'nlp', 'natural language', 'transformer',
        'openai', 'anthropic', 'midjourney', 'stable diffusion',
        'large language model', 'prompt engineering', 'diffusion model',
        'reinforcement learning', 'autonomous', 'robotics', 'algorithm'
    ]

    # Считаем совпадения
    matches = sum(1 for keyword in ai_keywords if keyword in content)

    # Также проверяем паттерны
    patterns = [
        r'\bAI\b', r'\bA\.I\.', r'machine learning', r'deep learning',
        r'generative (ai|model)', r'neural (network|net)'
    ]

    pattern_matches = sum(len(re.findall(pattern, content, re.IGNORECASE))
                          for pattern in patterns)

    # Статья считается AI, если есть достаточно совпадений
    return (matches >= 3) or (pattern_matches >= 2)


def save_articles_to_json(articles, filename=None):
    """Сохраняет статьи в JSON файл"""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"techcrunch_ai_{len(articles)}_articles_{timestamp}.json"

    # Конвертируем datetime в строки для JSON
    for article in articles:
        if 'published_time' in article and isinstance(article['published_time'], datetime):
            article['published_time'] = article['published_time'].isoformat()

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"Статьи сохранены в {filename}")
    return filename


def main():
    """Основная функция"""
    print("=" * 60)
    print("TECHCRUNCH AI ARTICLE PARSER")
    print("Парсинг пагинации /category/artificial-intelligence/page/N/")
    print("=" * 60)

    # Настройки
    TARGET_ARTICLES = 7000
    MAX_PAGES = 185  # 50 страниц × ~20 статей = ~1000 статей

    start_time = time.time()

    # Парсим статьи
    articles = parse_techcrunch_pagination(TARGET_ARTICLES, MAX_PAGES)

    # Сохраняем
    if articles:
        filename = save_articles_to_json(articles)

        # Статистика
        elapsed_time = time.time() - start_time
        avg_words = sum(a['word_count'] for a in articles) / len(articles)

        print(f"\n{'=' * 60}")
        print("СТАТИСТИКА:")
        print(f"Собрано статей: {len(articles)}")
        print(f"Время выполнения: {elapsed_time / 60:.1f} минут")
        print(f"Средняя длина статьи: {avg_words:.0f} слов")

        if articles:
            dates = [a['date'] for a in articles if 'date' in a]
            if dates:
                print(f"Диапазон дат: {min(dates)} - {max(dates)}")

        print(f"\nПервые 3 статьи:")
        for i, article in enumerate(articles[:3]):
            print(f"{i + 1}. {article['title'][:80]}...")
            print(f"   Дата: {article.get('date', 'N/A')}, Слов: {article['word_count']}")

        print(f"\nФайл: {filename}")
    else:
        print("Не удалось собрать статьи")


if __name__ == "__main__":
    main()