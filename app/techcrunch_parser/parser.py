import requests
import uuid
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Set
from .logger import logger
from .config import parser_config


def extract_full_article_text(session, url):
    """Извлекает полный текст статьи"""
    try:
        time.sleep(random.uniform(0.5, 0.8))
        response = session.get(url, timeout=15)

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        for element in soup.select('script, style, iframe, nav, footer, .advertisement, .share-buttons, .comments'):
            element.decompose()

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
                text_elements = content_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                text_parts = []

                for element in text_elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 30:
                        text_parts.append(text)

                if text_parts:
                    full_text = '\n\n'.join(text_parts)
                    if len(full_text) > 300:
                        return full_text

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
        logger.error(f"Ошибка получения текста: {e}")
        return None


class TechCrunchParser:
    """Парсер TechCrunch"""

    def __init__(self):
        self.session = None
        self._init_session()

    def _init_session(self):
        """Инициализация сессии"""
        self.session = requests.Session()
        self.session.headers.update(parser_config.HEADERS)

    def parse_articles(self, existing_ids: Set[str]) -> List[Dict]:
        """
        Парсит статьи с пагинацией

        Args:
            existing_ids: множество существующих ID статей

        Returns:
            список новых статей с текстом
        """
        logger.info("=" * 60)
        logger.info("Начинаю парсинг пагинации TechCrunch AI...")
        logger.info(f"Цель: {parser_config.TARGET_ARTICLES} статей")
        logger.info("=" * 60)

        all_articles = {}
        page = 1
        stop_parsing = False

        while len(all_articles) < parser_config.TARGET_ARTICLES and page <= parser_config.MAX_PAGES and not stop_parsing:
            if page == 1:
                url = "https://techcrunch.com/category/artificial-intelligence/"
            else:
                url = f"https://techcrunch.com/category/artificial-intelligence/page/{page}/"

            logger.info(f"Страница {page}: {url}")

            try:
                time.sleep(random.uniform(2, 4))
                response = self.session.get(url, timeout=15)

                if response.status_code == 404:
                    logger.warning(f"Страница {page} не найдена (404). Прекращаю парсинг.")
                    break

                if response.status_code != 200:
                    logger.warning(f"Ошибка {response.status_code}. Пропускаю страницу.")
                    page += 1
                    continue

                soup = BeautifulSoup(response.content, 'html.parser')

                article_elements = soup.find_all('li', class_='wp-block-post')

                if not article_elements:
                    article_elements = soup.select('article.post-block, .post-block')

                if not article_elements:
                    article_elements = soup.select('[class*="post-"]')

                if not article_elements:
                    logger.warning(f"На странице {page} статьи не найдены.")
                    break

                logger.info(f"Найдено статей: {len(article_elements)}")

                articles_on_page = 0

                for article_element in article_elements:
                    if len(all_articles) >= parser_config.TARGET_ARTICLES:
                        break

                    try:
                        link_element = article_element.select_one('a.loop-card__title-link')

                        if not link_element:
                            link_element = article_element.select_one('a[data-destinationlink]')

                        if not link_element:
                            link_element = article_element.select_one('a[href*="/202"]')

                        if not link_element:
                            continue

                        article_url = link_element.get('href', '')
                        if not article_url:
                            article_url = link_element.get('data-destinationlink', '')

                        if not article_url:
                            continue

                        if not article_url.startswith('http'):
                            article_url = 'https://techcrunch.com' + article_url

                        article_id = str(uuid.uuid5(uuid.NAMESPACE_URL, article_url))

                        if article_id in existing_ids:
                            if page > 1:
                                logger.info(f"Найдена существующая статья, останавливаю сбор ссылок")
                                stop_parsing = True
                                break
                            else:
                                continue

                        if article_url in all_articles:
                            continue

                        title_element = article_element.select_one('.loop-card__title')
                        if not title_element:
                            title_element = link_element

                        article_title = title_element.get_text(strip=True) if title_element else ""

                        if not article_title:
                            continue

                        date_from_url = article_url.split('/')[3:6]
                        if date_from_url and date_from_url[0][:2] == '20':
                            published_date = '-'.join(date_from_url)
                        else:
                            published_date = datetime.now().strftime('%Y-%m-%d')

                        all_articles[article_url] = {
                            "id": article_id,
                            "title": article_title,
                            "url": article_url,
                            "published_date": published_date,
                        }

                        articles_on_page += 1
                        logger.info(f"  Найдена: {article_title[:60]}...")

                    except Exception as e:
                        logger.error(f"Ошибка обработки статьи: {e}")
                        continue

                logger.info(f"На странице {page} добавлено статей: {articles_on_page}")
                logger.info(f"Всего собрано: {len(all_articles)}/{parser_config.TARGET_ARTICLES}")

                if not stop_parsing:
                    next_page_link = soup.select_one('.wp-block-query-pagination-next, a[rel="next"]')
                    if not next_page_link and len(article_elements) < 10:
                        logger.info("Нет следующей страницы. Прекращаю.")
                        break

                page += 1

            except requests.exceptions.Timeout:
                logger.warning(f"Таймаут на странице {page}. Пропускаю.")
                page += 1
                continue
            except Exception as e:
                logger.error(f"Критическая ошибка на странице {page}: {e}")
                break

        if not all_articles:
            logger.info("Нет статей для обработки")
            return []

        logger.info(f"\nНачинаю получение полного текста для {len(all_articles)} статей...")

        articles_with_text = []

        for i, (article_url, article_data) in enumerate(list(all_articles.items()), 1):
            try:
                logger.info(f"[{i}/{len(all_articles)}] Получаю текст: {article_data['title'][:60]}...")

                full_text = extract_full_article_text(self.session, article_url)

                if not full_text or len(full_text) < 500:
                    logger.warning(f"  Текст слишком короткий или не найден")
                    continue

                article_data["text"] = full_text
                article_data["word_count"] = len(full_text.split())
                article_data["parsed_at"] = datetime.now().isoformat()

                articles_with_text.append(article_data)

                logger.info(f"  Текст получен: {article_data['word_count']} слов")

                time.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                logger.error(f"  Ошибка получения текста: {e}")
                continue

        logger.info("=" * 60)
        logger.info(f"ПАРСИНГ ЗАВЕРШЕН!")
        logger.info(f"Всего собрано статей с текстом: {len(articles_with_text)}")
        logger.info("=" * 60)

        return articles_with_text
