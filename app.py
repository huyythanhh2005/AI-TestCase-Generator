import os
import platform
import subprocess

from config import config
from crawler import crawl_sync
from feature_extractor import FeatureExtractor
from llm_service import LLMService, OllamaNotRunningError
from requirement_engine import RequirementEngine
from use_case_engine import UseCaseEngine
from testcase_generator import TestCaseGenerator
from exporter import ExcelExporter, JiraExporter, TestRailExporter, export_json


def print_banner():
    print("=" * 80)
    print("   CÔNG CỤ TẠO TEST CASE TỰ ĐỘNG BẰNG AI (chạy 100% qua Ollama)")
    print("   Domain -> Website Crawler (Playwright) -> Crawl HTML + DOM")
    print("   -> Page Understanding (DOM Tree, Accessibility Tree, JS Events,")
    print("      Network Requests) -> Feature Extraction")
    print(f"   -> LLM (Ollama: {config.OLLAMA_MODEL}) -> Infer Requirements")
    print("   -> Use Case Synthesis -> Generate Test Cases")
    print("   -> Export (Excel / Jira / TestRail)")
    print("=" * 80)


def open_file(filepath):
    try:
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", filepath])
        else:
            subprocess.Popen(["xdg-open", filepath])
        print(f"✓ Đang tự động mở file: {filepath}")
    except Exception as e:
        print(f"[Cảnh báo] Không thể tự động mở file: {e}")


def main():
    print_banner()

    try:
        llm = LLMService()
    except OllamaNotRunningError as e:
        print(f"\n[LỖI] {e}")
        return

    url = input("Nhập URL website: ").strip()
    if not url:
        print("Lỗi: URL không được để trống.")
        return

    try:
        print("\n" + "=" * 80)
        print("BƯỚC 1-2: PLAYWRIGHT CRAWLER -> PAGE UNDERSTANDING")
        print("=" * 80)
        page_data = crawl_sync(url)
        stats = page_data.get("statistics", {})
        print(f"✓ Đã tải: {page_data.get('url')}")
        print(
            f"  Forms={stats.get('forms', 0)} Inputs={stats.get('inputs', 0)} "
            f"Buttons={stats.get('buttons', 0)} Links={stats.get('links', 0)} "
            f"Network={stats.get('network_requests', 0)} "
            f"JS_Events={stats.get('js_events', 0)}"
        )

        print("\n" + "=" * 80)
        print("BƯỚC 3: FEATURE EXTRACTION")
        print("=" * 80)
        features = FeatureExtractor().extract(page_data)
        print(f"✓ Trích xuất {len(features)} feature.")

        print("\n" + "=" * 80)
        print("BƯỚC 4: LLM - PHÂN LOẠI NGHIỆP VỤ WEBSITE")
        print("=" * 80)
        website_type = llm.detect_website_type(page_data) or "General"
        print(f"✓ Loại hình Website: {website_type.upper()}")

        print("\n" + "=" * 80)
        print("BƯỚC 5: REQUIREMENT INFERENCE (LLM chuẩn hoá yêu cầu)")
        print("=" * 80)
        requirements = RequirementEngine(llm).infer(features, website_type)
        print(f"✓ Suy luận {len(requirements)} yêu cầu nghiệp vụ.")

        print("\n" + "=" * 80)
        print("BƯỚC 5.5: USE CASE SYNTHESIS (gom yêu cầu thành Use Case)")
        print("=" * 80)
        use_cases = UseCaseEngine(llm).infer(requirements, website_type)
        print(f"✓ Tổng hợp {len(use_cases)} use case.")

        print("\n" + "=" * 80)
        print("BƯỚC 6: TEST CASE GENERATION")
        print("=" * 80)
        testcases = TestCaseGenerator(llm).run(requirements, website_type=website_type)

        if not testcases:
            print("[Cảnh báo] Không có test case nào được sinh ra. Dừng lại.")
            return
        print(f"✓ Đã sinh {len(testcases)} test case.")

        feature_to_uc = {}
        for uc in use_cases:
            for feat in uc.get("related_features", []):
                feature_to_uc.setdefault(str(feat).strip().lower(), uc["uc_id"])
        for tc in testcases:
            tc["use_case_ref"] = feature_to_uc.get(
                str(tc.get("feature", "")).strip().lower(), ""
            )

        print("\n" + "=" * 80)
        print("BƯỚC 7: EXPORT")
        print("=" * 80)

        target = config.EXPORT_TARGET

        if target == "json":
            output_file = export_json(requirements, testcases, use_cases=use_cases)
        elif target == "jira":
            result = JiraExporter().export(requirements, testcases)
            output_file = (
                f"{len(result['created_keys'])} issue đã tạo trên Jira "
                f"(project {config.JIRA_PROJECT_KEY})"
            )
        elif target == "testrail":
            result = TestRailExporter().export(requirements, testcases)
            output_file = (
                f"{len(result['created_case_ids'])} test case đã tạo trên "
                f"TestRail (project {config.TESTRAIL_PROJECT_ID})"
            )
        else:
            output_file = ExcelExporter().export(
                requirements=requirements, testcases=testcases, use_cases=use_cases
            )

        print("\n" + "=" * 80)
        print("HOÀN THÀNH")
        print("=" * 80)
        print(f" Kết quả xuất: {output_file}")
        print("=" * 80)

        if config.AUTO_OPEN_EXCEL and target not in ("json", "jira", "testrail"):
            open_file(output_file)

    except Exception as e:
        print(f"\n[LỖI NGHIÊM TRỌNG]: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()