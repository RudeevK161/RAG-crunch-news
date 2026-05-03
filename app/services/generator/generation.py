import torch
from typing import List, Dict, Any
from transformers import AutoModelForCausalLM, AutoTokenizer

from .prompt_build import PromptBuilder
from .monitor import metrics
from .semantic_cache import semantic_cache
from ..retrieval.search import retriever
from app.core.generation_config import generation_config
from .api_client import APIClient


def clean_answer(answer: str) -> str:
    """Очистка ответа от лишних префиксов"""
    prefixes = ["Answer:", "Detailed Answer:", "Comprehensive Answer:", "Concise Answer:"]
    for prefix in prefixes:
        if answer.startswith(prefix):
            answer = answer.replace(prefix, "").strip()
    return '\n'.join([line.strip() for line in answer.split('\n') if line.strip()])


class RAGGenerator:
    def __init__(self):
        self.config = generation_config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.prompt_builder = PromptBuilder()
        self.mode = self.config.MODE

        if self.mode == "local":
            self._load_model()
            self.api_client = None
        else:
            self.model = self.tokenizer = None
            self.api_client = APIClient()

        print(f"RAG Generator in {self.mode.upper()} mode")

    def _load_model(self):
        """Загрузка локальной модели"""
        print(f"Loading {self.config.LLM_MODEL}...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.LLM_MODEL, trust_remote_code=True, padding_side="left"
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.LLM_MODEL, trust_remote_code=True,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None
        )
        if torch.cuda.is_available():
            self.model = self.model.to(self.device)
        self.model.eval()

    def _get_params(self, **kwargs):
        """Получение параметров с дефолтами из конфига"""
        return {
            'max_new_tokens': kwargs.get('max_new_tokens', self.config.DEFAULT_MAX_NEW_TOKENS),
            'temperature': kwargs.get('temperature', self.config.DEFAULT_TEMPERATURE),
            'top_p': kwargs.get('top_p', self.config.DEFAULT_TOP_P),
            'repetition_penalty': kwargs.get('repetition_penalty', self.config.DEFAULT_REPETITION_PENALTY)
        }

    def _generate(self, prompt: str, **params) -> str:
        """Единый метод генерации (локальный или API)"""
        p = self._get_params(**params)

        if self.mode == "local":
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True,
                                    max_length=self.config.MAX_CONTEXT_TOKEN)
            if torch.cuda.is_available():
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=p['max_new_tokens'],
                    temperature=p['temperature'],
                    do_sample=p['temperature'] > 0,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    top_p=p['top_p'] if p['temperature'] > 0 else 1.0,
                    repetition_penalty=p['repetition_penalty']
                )
            return self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()
        else:
            return self.api_client.generate(prompt, **p)

    def generate(self, question: str, contexts: List[Dict] = None, style: str = "detailed",
                 use_cache: bool = True, **params) -> Dict[str, Any]:
        """Основной метод генерации"""
        metrics.total_requests += 1
        start_time = metrics.start_timer()

        try:
            if use_cache and question:
                cached_answer, score = semantic_cache.search(question)
                if cached_answer:
                    metrics.cache_hits += 1
                    metrics.end_timer(start_time)
                    return {
                        "question": question, "answer": cached_answer, "style": style,
                        "contexts_used": len(contexts) if contexts else 0, "cached": True,
                        "mode": self.mode, **self._get_params(**params)
                    }
                metrics.cache_misses += 1

            prompt = self.prompt_builder.build_prompt(question, contexts, style)
            answer = clean_answer(self._generate(prompt, **params))

            if use_cache and question and answer:
                semantic_cache.save(question, answer)

            metrics.end_timer(start_time)
            return {
                "question": question, "answer": answer, "style": style,
                "contexts_used": len(contexts) if contexts else 0, "cached": False,
                "mode": self.mode, **self._get_params(**params)
            }
        except Exception as e:
            metrics.errors += 1
            metrics.end_timer(start_time)
            return {"question": question, "answer": f"Error: {str(e)}", "style": style,
                    "contexts_used": len(contexts) if contexts else 0, "error": str(e), "mode": self.mode}

    def generate_with_retrieval(self, question: str, style: str = "detailed", use_cache: bool = True, **params) -> Dict[
        str, Any]:
        """Генерация c автоматическим поиском"""
        return self.generate(question, retriever(question), style, use_cache, **params)


rag_generator = RAGGenerator()