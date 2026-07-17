import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ==========================================================
# Thư mục gốc
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
SCREENSHOT_DIR = BASE_DIR / "screenshots"
LOG_DIR = BASE_DIR / "logs"
CACHE_DIR = BASE_DIR / "cache"

for folder in (OUTPUT_DIR, SCREENSHOT_DIR, LOG_DIR, CACHE_DIR):
    folder.mkdir(parents=True, exist_ok=True)

# ==========================================================
# LLM - Ollama
# ==========================================================

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

OLLAMA_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("OLLAMA_FALLBACK_MODELS", "").split(",")
    if m.strip()
]

OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
TOP_P = float(os.getenv("TOP_P", "0.9"))
REPEAT_PENALTY = float(os.getenv("REPEAT_PENALTY", "1.1"))
OLLAMA_SEED = int(os.getenv("OLLAMA_SEED", "42"))

OLLAMA_NUM_THREAD = int(os.getenv("OLLAMA_NUM_THREAD", "12"))
OLLAMA_NUM_GPU = int(os.getenv("OLLAMA_NUM_GPU", "999"))
OLLAMA_NUM_BATCH = int(os.getenv("OLLAMA_NUM_BATCH", "512"))

OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "6144"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "6144"))
MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "180"))
OLLAMA_OPTIONS = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P,
    "repeat_penalty": REPEAT_PENALTY,
    "num_ctx": OLLAMA_NUM_CTX,
    "num_predict": OLLAMA_NUM_PREDICT,
    "num_thread": OLLAMA_NUM_THREAD,
    "num_gpu": OLLAMA_NUM_GPU,
    "num_batch": OLLAMA_NUM_BATCH,
    "num_keep": -1,
    "seed": OLLAMA_SEED,
}

LLM_CHUNK_SIZE = int(os.getenv("LLM_CHUNK_SIZE", "15"))
TESTCASE_CHUNK_SIZE = int(os.getenv("TESTCASE_CHUNK_SIZE", "3"))

# ==========================================================
# Playwright (Crawler / Page Understanding)
# ==========================================================

HEADLESS = os.getenv("HEADLESS", "true").lower() != "false"
VIEWPORT = {"width": 1920, "height": 1080}
PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "60000"))
WAIT_TIME = int(os.getenv("WAIT_TIME", "2000"))

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0 Safari/537.36"
)

CAPTURE_ACCESSIBILITY_TREE = True

# ==========================================================
# Crawler - đa trang (tuỳ chọn)
# ==========================================================

MAX_PAGES = int(os.getenv("MAX_PAGES", "5"))
CRAWL_INTERNAL_PAGES = os.getenv("CRAWL_INTERNAL_PAGES", "false").lower() == "true"

# ==========================================================
# Test Case Generation
# ==========================================================

MIN_TESTCASE = int(os.getenv("MIN_TESTCASE", "30"))
REMOVE_DUPLICATE = True

STRICT_GROUNDING = os.getenv("STRICT_GROUNDING", "true").lower() == "true"

ENABLE_NEGATIVE_TEST = True
ENABLE_BOUNDARY_TEST = True
ENABLE_EXCEPTION_TEST = True
ENABLE_SECURITY_TEST = True
ENABLE_ACCESSIBILITY_TEST = True
ENABLE_PERFORMANCE_TEST = True
ENABLE_API_TEST = True

# ==========================================================
# Export
# ==========================================================

EXPORT_TARGET = os.getenv("EXPORT_TARGET", "excel").lower()
EXCEL_NAME = "AI_TestCase_Report"
DATE_FORMAT = "%Y%m%d_%H%M%S"
AUTO_OPEN_EXCEL = os.getenv("AUTO_OPEN_EXCEL", "true").lower() == "true"

JIRA_URL = os.getenv("JIRA_URL", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "")
JIRA_ISSUE_TYPE = os.getenv("JIRA_ISSUE_TYPE", "Test")

TESTRAIL_URL = os.getenv("TESTRAIL_URL", "")
TESTRAIL_EMAIL = os.getenv("TESTRAIL_EMAIL", "")
TESTRAIL_API_KEY = os.getenv("TESTRAIL_API_KEY", "")
TESTRAIL_PROJECT_ID = os.getenv("TESTRAIL_PROJECT_ID", "")
TESTRAIL_SUITE_ID = os.getenv("TESTRAIL_SUITE_ID", "")

# ==========================================================
# Debug / Logging
# ==========================================================

DEBUG = os.getenv("DEBUG", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class Config:
    BASE_DIR = BASE_DIR
    OUTPUT_DIR = OUTPUT_DIR
    SCREENSHOT_DIR = SCREENSHOT_DIR
    LOG_DIR = LOG_DIR
    CACHE_DIR = CACHE_DIR
    OLLAMA_OPTIONS = OLLAMA_OPTIONS

    OLLAMA_BASE_URL = OLLAMA_BASE_URL
    OLLAMA_MODEL = OLLAMA_MODEL
    OLLAMA_FALLBACK_MODELS = OLLAMA_FALLBACK_MODELS
    OLLAMA_NUM_CTX = OLLAMA_NUM_CTX
    OLLAMA_KEEP_ALIVE = OLLAMA_KEEP_ALIVE

    TEMPERATURE = TEMPERATURE
    TOP_P = TOP_P
    REPEAT_PENALTY = REPEAT_PENALTY

    OLLAMA_SEED = OLLAMA_SEED
    OLLAMA_NUM_THREAD = OLLAMA_NUM_THREAD
    OLLAMA_NUM_GPU = OLLAMA_NUM_GPU
    OLLAMA_NUM_BATCH = OLLAMA_NUM_BATCH
    OLLAMA_NUM_PREDICT = OLLAMA_NUM_PREDICT
    MAX_OUTPUT_TOKENS = MAX_OUTPUT_TOKENS
    MAX_RETRY = MAX_RETRY
    REQUEST_TIMEOUT = REQUEST_TIMEOUT
    LLM_CHUNK_SIZE = LLM_CHUNK_SIZE
    TESTCASE_CHUNK_SIZE = TESTCASE_CHUNK_SIZE

    HEADLESS = HEADLESS
    VIEWPORT = VIEWPORT
    PAGE_TIMEOUT = PAGE_TIMEOUT
    WAIT_TIME = WAIT_TIME
    USER_AGENT = USER_AGENT
    CAPTURE_ACCESSIBILITY_TREE = CAPTURE_ACCESSIBILITY_TREE

    MAX_PAGES = MAX_PAGES
    CRAWL_INTERNAL_PAGES = CRAWL_INTERNAL_PAGES

    MIN_TESTCASE = MIN_TESTCASE
    REMOVE_DUPLICATE = REMOVE_DUPLICATE
    STRICT_GROUNDING = STRICT_GROUNDING
    ENABLE_NEGATIVE_TEST = ENABLE_NEGATIVE_TEST
    ENABLE_BOUNDARY_TEST = ENABLE_BOUNDARY_TEST
    ENABLE_EXCEPTION_TEST = ENABLE_EXCEPTION_TEST
    ENABLE_SECURITY_TEST = ENABLE_SECURITY_TEST
    ENABLE_ACCESSIBILITY_TEST = ENABLE_ACCESSIBILITY_TEST
    ENABLE_PERFORMANCE_TEST = ENABLE_PERFORMANCE_TEST
    ENABLE_API_TEST = ENABLE_API_TEST

    EXPORT_TARGET = EXPORT_TARGET
    EXCEL_NAME = EXCEL_NAME
    DATE_FORMAT = DATE_FORMAT
    AUTO_OPEN_EXCEL = AUTO_OPEN_EXCEL

    JIRA_URL = JIRA_URL
    JIRA_EMAIL = JIRA_EMAIL
    JIRA_API_TOKEN = JIRA_API_TOKEN
    JIRA_PROJECT_KEY = JIRA_PROJECT_KEY
    JIRA_ISSUE_TYPE = JIRA_ISSUE_TYPE

    TESTRAIL_URL = TESTRAIL_URL
    TESTRAIL_EMAIL = TESTRAIL_EMAIL
    TESTRAIL_API_KEY = TESTRAIL_API_KEY
    TESTRAIL_PROJECT_ID = TESTRAIL_PROJECT_ID
    TESTRAIL_SUITE_ID = TESTRAIL_SUITE_ID

    DEBUG = DEBUG
    LOG_LEVEL = LOG_LEVEL


config = Config()