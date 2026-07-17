import hashlib
import json
import time
import requests
from config import config
from utils import info, warning, safe_json_load

_LLM_CACHE_DIR = config.CACHE_DIR / "llm_cache"
_LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_REQ_SCHEMA = '{"req_id":"","feature":"","module":"","description":"","priority":"","business_rules":[],"validation_rules":[]}'
_TC_SCHEMA = '{"feature":"","module":"","scenario":"","type":"","priority":"","steps":[""],"expected_result":""}'
_UC_SCHEMA = '{"title":"","actor":"","description":"","preconditions":[""],"main_flow":[""],"postconditions":[""],"related_features":[""]}'

_GROUNDING_RULE = (
    "QUY TẮC BẮT BUỘC - CHỈ DÙNG DỮ LIỆU THẬT:\n"
    "- Mỗi requirement có field elements: dữ liệu THẬT từ website.\n"
    "- TUYỆT ĐỐI KHÔNG bịa thêm trường, nút, link, API không tồn tại.\n"
    "- Nếu thiếu dữ liệu, ghi 'Không đủ dữ liệu' thay vì đoán.\n"
    "- Field feature: PHẢI copy NGUYÊN VĂN, không đổi 1 ký tự.\n"
)


def _cache_path(prompt, model):
    h = hashlib.sha256(f"{model}::{prompt}".encode("utf-8")).hexdigest()
    return _LLM_CACHE_DIR / f"{h}.txt"


def _load_cache(prompt, model):
    path = _cache_path(prompt, model)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def _save_cache(prompt, model, text):
    try:
        _cache_path(prompt, model).write_text(text or "", encoding="utf-8")
    except Exception:
        pass


class OllamaNotRunningError(RuntimeError):
    """Không kết nối được tới Ollama server."""
    pass


class LLMService:
    def __init__(self, skip_health_check=False):
        self.base_url = config.OLLAMA_BASE_URL
        self.temperature = config.TEMPERATURE
        self.top_p = config.TOP_P
        self.max_tokens = config.MAX_OUTPUT_TOKENS
        self.max_retry = max(1, config.MAX_RETRY)
        self.num_ctx = config.OLLAMA_NUM_CTX
        self.keep_alive = config.OLLAMA_KEEP_ALIVE
        self.timeout = config.REQUEST_TIMEOUT
        self.chunk_size = max(1, config.LLM_CHUNK_SIZE)

        self.models = [config.OLLAMA_MODEL] + [
            m for m in config.OLLAMA_FALLBACK_MODELS if m != config.OLLAMA_MODEL
        ]
        self._unavailable = set()

        if not skip_health_check:
            self._check_server_and_models()

    def _check_server_and_models(self):
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except Exception as e:
            raise OllamaNotRunningError(
                f"Không kết nối được tới Ollama tại {self.base_url}. "
                "Hãy chắc chắn Ollama đã được cài và đang chạy, rồi thử lại. "
                f"Chi tiết lỗi: {e}"
            )
        info(f"LLM sẵn sàng qua Ollama ({self.base_url}), model chính: {self.models[0]}")

    def ask(self, prompt, max_tokens=None, json_mode=True):
        tokens = self.max_tokens if max_tokens is None else max_tokens
        cached = _load_cache(prompt, self.models[0])
        if cached is not None:
            info("  (cache) Đã có kết quả từ lần chạy trước.")
            return cached

        last_error = None
        for model in self.models:
            if model in self._unavailable:
                continue
            for attempt in range(self.max_retry):
                try:
                    payload = {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "keep_alive": self.keep_alive,
                        "options": {
                            "temperature": self.temperature,
                            "top_p": self.top_p,
                            "num_predict": tokens,
                            "num_ctx": self.num_ctx,
                        },
                    }
                    if json_mode:
                        payload["format"] = "json"

                    resp = requests.post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                        timeout=self.timeout,
                    )

                    if resp.status_code == 404:
                        self._unavailable.add(model)
                        warning(f"Model '{model}' chưa có. Chạy `ollama pull {model}` rồi thử lại.")
                        break

                    resp.raise_for_status()
                    data = resp.json()
                    text = (data.get("message") or {}).get("content", "")

                    if not text:
                        raise RuntimeError(f"Model '{model}' trả về nội dung rỗng.")

                    _save_cache(prompt, self.models[0], text)
                    return text

                except Exception as e:
                    last_error = e
                    warning(f"[{model}] Retry {attempt + 1}/{self.max_retry}: {e}")
                    time.sleep(2)

        raise last_error or OllamaNotRunningError(
            "Tất cả model Ollama đều lỗi/không khả dụng."
        )

    def ask_json(self, prompt, max_tokens=None):
        text = self.ask(prompt, max_tokens=max_tokens, json_mode=True)
        return safe_json_load(text)

    def _ask_json_in_chunks(self, build_prompt, items, chunk_size=None, max_tokens=None):
        items = items or []
        if not items:
            return []
        size = chunk_size or self.chunk_size
        chunks = [items[i:i + size] for i in range(0, len(items), size)]
        total = len(chunks)
        merged = []
        for idx, chunk in enumerate(chunks, start=1):
            info(f"  -> Batch {idx}/{total} ({len(chunk)} items)...")
            prompt = build_prompt(chunk)
            try:
                data = self.ask_json(prompt, max_tokens=max_tokens)
            except Exception as e:
                warning(f"Batch {idx}/{total} thất bại: {e}")
                continue
            if isinstance(data, list):
                merged.extend(item for item in data if isinstance(item, dict))
            elif isinstance(data, dict):
                merged.append(data)
        return merged

    _WEBSITE_CATEGORIES = [
        "Ecommerce", "Banking", "Education", "Hospital", "Government",
        "CRM", "CMS", "Blog", "Portfolio", "LandingPage", "General",
    ]

    def detect_website_type(self, page_data):
        prompt = (
            f"Website: {page_data.get('title', '')}\n"
            f"Forms: {len(page_data.get('forms', []))} "
            f"Buttons: {len(page_data.get('buttons', []))} "
            f"Tables: {len(page_data.get('tables', []))} \n"
            f"Classify vào MỘT trong các category: {','.join(self._WEBSITE_CATEGORIES)}.\n"
            f"Reply with ONLY the category word."
        )
        result = (self.ask(prompt, max_tokens=40, json_mode=False) or "").strip()
        lower_result = result.lower()
        for category in self._WEBSITE_CATEGORIES:
            if category.lower() in lower_result:
                return category
        return "General"

    def analyze_requirements(self, features):
        def build_prompt(chunk):
            data_json = json.dumps(chunk, ensure_ascii=False, separators=(',', ':'))
            return (
                f"ISTQB Test Analyst. Analyze features, infer requirements.\n\n"
                f"{_GROUNDING_RULE}\n\n"
                f"Features:\n{data_json}\n\n"
                f"Return JSON array: {_REQ_SCHEMA}\nNo explanation."
            )
        return self._ask_json_in_chunks(build_prompt, features)

    def generate_use_cases(self, website_type, module, requirements, min_uc=1, max_uc=3):
        trimmed = [
            {"feature": r.get("feature", ""), "description": r.get("description", "")}
            for r in requirements
        ]
        data_json = json.dumps(trimmed, ensure_ascii=False, separators=(',', ':'))
        prompt = (
            f"Business Analyst. Website: {website_type}. Module: {module}.\n\n"
            f"{_GROUNDING_RULE}\n\n"
            f"Features:\n{data_json}\n\n"
            f"Generate {min_uc}-{max_uc} USE CASES.\n"
            f"Return JSON array: {_UC_SCHEMA}\nNo explanation."
        )
        return self.ask_json(prompt)

    def generate_testcases(self, website_type, requirements):
        def build_prompt(chunk):
            data_json = json.dumps(chunk, ensure_ascii=False, separators=(',', ':'))
            return (
                f"Senior QA. ISTQB. Website: {website_type}\n\n"
                f"{_GROUNDING_RULE}\n\n"
                f"Requirements:\n{data_json}\n\n"
                f"Generate test cases (Positive, Negative, Boundary, Equivalence, Error, Exception, UI).\n"
                f"Return JSON array: {_TC_SCHEMA}\nNo explanation."
            )
        return self._ask_json_in_chunks(
            build_prompt, requirements, chunk_size=config.TESTCASE_CHUNK_SIZE
        )
