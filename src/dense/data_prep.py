import re
from typing import List
import logging

logger = logging.getLogger(__name__)


class TextChunker:
    """Класс для разбиения текста на чанки по абзацам"""

    def __init__(self, max_chunk_size: int = 1500, overlap: int = 150):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def split_into_paragraphs(self, text: str) -> List[str]:
        paragraphs = re.split(r'\n\s*\n', text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        return paragraphs

    def merge_paragraphs_to_chunks(self, paragraphs: List[str]) -> List[str]:
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            if para_size > self.max_chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0

                sentences = re.split(r'(?<=[.!?])\s+', para)
                temp_chunk = []
                temp_size = 0

                for sent in sentences:
                    sent_size = len(sent)
                    if temp_size + sent_size > self.max_chunk_size and temp_chunk:
                        chunks.append(' '.join(temp_chunk))
                        overlap_text = temp_chunk[-1] if temp_chunk else ''
                        temp_chunk = [overlap_text, sent] if overlap_text else [sent]
                        temp_size = len(overlap_text) + sent_size if overlap_text else sent_size
                    else:
                        temp_chunk.append(sent)
                        temp_size += sent_size

                if temp_chunk:
                    chunks.append(' '.join(temp_chunk))

            elif current_size + para_size + 2 > self.max_chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))

                overlap_text = current_chunk[-1] if current_chunk else ''
                if overlap_text and len(overlap_text) <= self.overlap:
                    current_chunk = [overlap_text, para]
                    current_size = len(overlap_text) + para_size + 2
                else:
                    current_chunk = [para]
                    current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size + 2

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def chunk_text(self, text: str) -> List[str]:
        paragraphs = self.split_into_paragraphs(text)
        chunks = self.merge_paragraphs_to_chunks(paragraphs)
        return chunks


def clean_text_for_embedding(text):
    if not isinstance(text, str):
        return ""

    text = re.sub(r'http\S+|www\S+|https\S+|@\S+', '', text, flags=re.MULTILINE)

    text = re.sub(r'\(\d+\)', '', text)

    text = re.sub(r'Subscribe to.*casts\.', '', text, flags=re.DOTALL)
    text = re.sub(r'Listen to.*episode.*:', '', text, flags=re.DOTALL)
    text = re.sub(r'You also can follow.*@\w+', '', text)

    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'\n+', ' ', text)

    text = ' '.join(text.split())

    return text.strip()