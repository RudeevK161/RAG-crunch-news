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
            return f"""Answer the question using ONLY the information from the sources.

**STRICT RULES:**
1. Use ONLY facts explicitly stated in the sources.
2. Do NOT add assumptions, general knowledge, or interpretations.
3. Copy all numbers, names, and specific details EXACTLY as written.
4. Answer ONLY the question — do not include unrelated information.

**STYLE:**
- Be concise and precise.
- Do not repeat the question.
- Do not summarize the entire context.
- Prefer short factual statements over long explanations.

**PROCESS (follow internally):**
- Identify the parts of the sources directly relevant to the question.
- Ignore irrelevant information.
- Extract and combine only the necessary facts.

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