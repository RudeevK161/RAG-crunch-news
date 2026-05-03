from typing import List, Dict


class PromptBuilder:
    """Построитель промптов для разных стилей ответов"""

    @staticmethod
    def build_prompt(
            question: str,
            contexts: List[Dict] = None,
            style: str = "detailed"
    ) -> str:
        """
        Построение промпта для генерации

        Args:
            question: Вопрос пользователя
            contexts: Список релевантных текстов (опционально)
            style: Стиль ответа (detailed, concise, comprehensive)
        """
        if not contexts:
            return PromptBuilder._build_without_context(question, style)

        # Форматирование контекста
        context_parts = []
        for i, ctx in enumerate(contexts, 1):

            text_preview = ctx.get('text_preview', '')
            if text_preview:
                context_parts.append(f"[Source {i}]\n{text_preview}")

        context = "\n\n".join(context_parts)

        if style == "detailed":
            return f"""You are an expert IT analyst. Based on the provided sources, generate a detailed answer.

**Sources:**
{context}

**Question:**
{question}

**Detailed Answer:**"""

        elif style == "comprehensive":
            return f"""You are a senior technology journalist. Create a comprehensive response based on the sources below.

**Sources:**
{context}

**Question:**
{question}

**Comprehensive Answer:**"""

        else:  # concise
            return f"""Based on the sources below, answer the question concisely.

**Sources:**
{context}

**Question:**
{question}

**Answer:**"""

    @staticmethod
    def _build_without_context(question: str, style: str) -> str:
        """Промпт без контекста"""
        if style == "concise":
            return f"Question: {question}\n\nAnswer:"
        elif style == "comprehensive":
            return f"Question: {question}\n\nProvide a comprehensive answer based on your knowledge.\n\nAnswer:"
        else:
            return f"Question: {question}\n\nPlease provide a clear and informative answer.\n\nAnswer:"