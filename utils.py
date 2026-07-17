import json
import logging
import re
from pathlib import Path
from config import config

# ==========================================================
# Logger
# ==========================================================

logger = logging.getLogger("AITestGenerator")

if not logger.handlers:
    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s : %(message)s")
    
    file_handler = logging.FileHandler(
        config.LOG_DIR / "system.log", encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def info(msg):
    logger.info(msg)


def warning(msg):
    logger.warning(msg)


def error(msg):
    logger.error(msg)


# ==========================================================
# JSON files
# ==========================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ==========================================================
# LLM output cleanup
# ==========================================================

def clean_markdown(text):
    if not text:
        return ""
    text = text.replace("```json", "").replace("```", "")
    return text.strip()


def safe_json_load(text):
    """Cố gắng parse JSON, luôn trả về list."""
    if isinstance(text, list):
        return text
    if isinstance(text, dict):
        return [text]

    if not text or not isinstance(text, str):
        return []

    text = text.strip()
    if not text:
        return []

    # Parse sạch
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception:
        pass

    # Fix common JSON syntax errors
    try:
        fixed = text.replace("'", '"')
        fixed = re.sub(r",\s*}", "}", fixed)
        fixed = re.sub(r",\s*]", "]", fixed)
        parsed = json.loads(fixed)
        return parsed if isinstance(parsed, list) else [parsed]
    except Exception:
        pass

    warning("Không parse được JSON từ LLM, trả về danh sách rỗng.")
    return []


# ==========================================================
# Test case helpers
# ==========================================================

def filter_invalid_testcases(testcases):
    """Loại bỏ những entry rỗng/hỏng."""
    kept = []
    dropped = 0

    for tc in testcases:
        if not isinstance(tc, dict):
            dropped += 1
            continue

        scenario = str(tc.get("scenario") or "").strip()
        steps = tc.get("steps") or []
        has_steps = isinstance(steps, list) and any(str(s).strip() for s in steps)

        if not scenario or not has_steps:
            dropped += 1
            continue

        kept.append(tc)

    if dropped:
        warning(f"Đã loại {dropped} test case rỗng/thiếu scenario hoặc steps.")

    return kept


def remove_duplicate_testcases(testcases):
    """Loại bỏ test case trùng lặp."""
    result = []
    cache = set()

    for tc in testcases:
        if not isinstance(tc, dict):
            continue
        key = (
            str(tc.get("feature", "")).strip().lower(),
            str(tc.get("scenario", "")).strip().lower(),
            str(tc.get("type", "Functional")).strip().lower(),
        )
        if key in cache:
            continue
        cache.add(key)
        result.append(tc)

    return result


def filter_grounded_testcases(testcases, requirements):
    """Lọc hậu kiểm chống hallucination."""
    known = {
        str(r.get("feature", "")).strip().lower()
        for r in (requirements or [])
        if r.get("feature")
    }

    if not known:
        return testcases

    kept, dropped = [], 0
    for tc in testcases:
        feature = str(tc.get("feature", "")).strip().lower()
        if feature and feature in known:
            kept.append(tc)
        else:
            dropped += 1

    if dropped:
        warning(
            f"Đã loại {dropped} test case không khớp feature nào từ dữ "
            "liệu crawl thực tế."
        )

    return kept


def assign_tc_id(testcases, prefix="TC"):
    """Gán ID cho test case."""
    for i, tc in enumerate(testcases, 1):
        tc["tc_id"] = f"{prefix}{i:05d}"
    return testcases
