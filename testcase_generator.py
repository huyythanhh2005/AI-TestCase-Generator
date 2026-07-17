from config import config
from llm_service import LLMService
from utils import (
    info,
    warning,
    assign_tc_id,
    remove_duplicate_testcases,
    filter_grounded_testcases,
    filter_invalid_testcases,
)


class TestCaseGenerator:
    def __init__(self, llm=None):
        self.llm = llm or LLMService()

    def run(self, requirements, website_type="General"):
        info(f"Test Case Generation: website_type={website_type}")

        requirements = requirements or []
        if not requirements:
            warning("Không có requirement nào để sinh test case.")
            return []

        all_cases = []
        all_cases.extend(self._safe_call(self.llm.generate_testcases, website_type, requirements))

        all_cases = filter_invalid_testcases(all_cases)
        if config.REMOVE_DUPLICATE:
            all_cases = remove_duplicate_testcases(all_cases)
        if config.STRICT_GROUNDING:
            all_cases = filter_grounded_testcases(all_cases, requirements)

        all_cases = assign_tc_id(all_cases)

        if len(all_cases) < config.MIN_TESTCASE:
            warning(f"Chỉ sinh được {len(all_cases)} test case (< MIN_TESTCASE={config.MIN_TESTCASE}).")

        info(f"Đã sinh {len(all_cases)} test case.")
        return all_cases

    def _safe_call(self, fn, *args):
        try:
            result = fn(*args)
            return result if isinstance(result, list) else []
        except Exception as e:
            warning(f"{fn.__name__} thất bại: {e}")
            return []
