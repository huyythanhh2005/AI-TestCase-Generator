from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from config import config
from utils import save_json, info, warning


class ExcelExporter:
    def __init__(self):
        self.output_dir = config.OUTPUT_DIR

    def export(self, requirements, testcases, use_cases=None):
        use_cases = use_cases or []
        wb = Workbook()
        wb.remove(wb.active)

        self._write_summary(wb.create_sheet("Tóm tắt"), requirements, testcases, use_cases)
        self._write_use_cases(wb.create_sheet("Use Case"), use_cases)
        self._write_requirements(wb.create_sheet("Yêu cầu"), requirements)
        self._write_testcases(wb.create_sheet("Test Cases"), testcases)

        timestamp = datetime.now().strftime(config.DATE_FORMAT)
        filename = f"{config.EXCEL_NAME}_{timestamp}.xlsx"
        filepath = self.output_dir / filename
        wb.save(filepath)
        info(f"Đã xuất Excel: {filepath}")
        return str(filepath)

    def _header_style(self, cell):
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def _auto_width(self, sheet):
        for column in sheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                if cell.value is not None:
                    val = str(cell.value)
                    max_length = max(max_length, len(val))
            sheet.column_dimensions[column_letter].width = min(max(max_length + 3, 12), 65)

    def _write_summary(self, sheet, requirements, testcases, use_cases=None):
        use_cases = use_cases or []
        sheet["A1"] = "BÁO CÁO KIỂM THỬ TỰ ĐỘNG"
        sheet["A1"].font = Font(bold=True, size=14, color="FFFFFF")
        sheet["A1"].fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        sheet.merge_cells("A1:C1")

        row = 3
        for col_idx, header in enumerate(["Hạng mục", "Số lượng", "Ghi chú"], 1):
            self._header_style(sheet.cell(row=row, column=col_idx, value=header))

        metrics = [
            ("Tổng số yêu cầu hệ thống", len(requirements), "Feature Extraction + LLM"),
            ("Tổng số Use Case", len(use_cases), "Use Case Synthesis"),
            ("Tổng số kịch bản (Test Cases)", len(testcases), "Sinh bởi AI"),
            ("Thời gian khởi tạo tệp", datetime.now(), "Real-time"),
        ]
        for metric in metrics:
            row += 1
            sheet.cell(row=row, column=1, value=metric[0]).font = Font(bold=True)
            sheet.cell(row=row, column=2, value=metric[1])
            sheet.cell(row=row, column=3, value=metric[2])

        self._auto_width(sheet)

    def _write_use_cases(self, sheet, use_cases):
        headers = ["Mã UC", "Tên Use Case", "Actor", "Module", "Mô tả"]
        for col, header in enumerate(headers, 1):
            self._header_style(sheet.cell(row=1, column=col, value=header))
        for row, uc in enumerate(use_cases, 2):
            sheet.cell(row=row, column=1, value=uc.get("uc_id", ""))
            sheet.cell(row=row, column=2, value=uc.get("title", ""))
            sheet.cell(row=row, column=3, value=uc.get("actor", ""))
            sheet.cell(row=row, column=4, value=uc.get("module", ""))
            sheet.cell(row=row, column=5, value=uc.get("description", ""))
        self._auto_width(sheet)

    def _write_requirements(self, sheet, requirements):
        headers = ["Tính năng", "Phân vùng Module", "Mô tả", "Quy tắc nghiệp vụ"]
        for col, header in enumerate(headers, 1):
            self._header_style(sheet.cell(row=1, column=col, value=header))
        for row, req in enumerate(requirements, 2):
            sheet.cell(row=row, column=1, value=req.get("feature", ""))
            sheet.cell(row=row, column=2, value=req.get("module", ""))
            sheet.cell(row=row, column=3, value=req.get("description", ""))
            b_rules = req.get("business_rules") or []
            sheet.cell(row=row, column=4, value="\n".join(b_rules) if isinstance(b_rules, list) else str(b_rules))
        self._auto_width(sheet)

    def _write_testcases(self, sheet, testcases):
        headers = ["Mã TC", "Tính năng", "Kịch bản", "Phân loại", "Mức ưu tiên", "Các bước", "Kết quả mong đợi"]
        for col, header in enumerate(headers, 1):
            self._header_style(sheet.cell(row=1, column=col, value=header))
        for row, tc in enumerate(testcases, 2):
            sheet.cell(row=row, column=1, value=tc.get("tc_id", f"TC_{row - 1:05d}"))
            sheet.cell(row=row, column=2, value=tc.get("feature", ""))
            sheet.cell(row=row, column=3, value=tc.get("scenario", ""))
            sheet.cell(row=row, column=4, value=tc.get("type", "Functional"))
            sheet.cell(row=row, column=5, value=tc.get("priority", "Medium"))
            steps = tc.get("steps") or []
            steps_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps)) if isinstance(steps, list) else str(steps)
            sheet.cell(row=row, column=6, value=steps_text)
            sheet.cell(row=row, column=7, value=tc.get("expected_result", ""))
        self._auto_width(sheet)


class JiraExporter:
    def __init__(self):
        self.base_url = (config.JIRA_URL or "").rstrip("/")
        self.auth = HTTPBasicAuth(config.JIRA_EMAIL, config.JIRA_API_TOKEN)
        self.project_key = config.JIRA_PROJECT_KEY
        self.issue_type = config.JIRA_ISSUE_TYPE

    def export(self, requirements, testcases):
        if not (self.base_url and config.JIRA_EMAIL and config.JIRA_API_TOKEN and self.project_key):
            raise RuntimeError("Thiếu cấu hình Jira.")
        created, failed = [], []
        for tc in testcases:
            payload = self._build_issue_payload(tc)
            try:
                resp = requests.post(
                    f"{self.base_url}/rest/api/3/issue",
                    json=payload,
                    auth=self.auth,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    created.append(resp.json().get("key"))
                else:
                    failed.append({"tc_id": tc.get("tc_id"), "error": resp.text[:300]})
            except Exception as e:
                failed.append({"tc_id": tc.get("tc_id"), "error": str(e)})
        info(f"Jira: đã tạo {len(created)}/{len(testcases)} issue.")
        return {"created_keys": created, "failed": failed}

    def _build_issue_payload(self, tc):
        steps = tc.get("steps") or []
        steps_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
        description_text = f"Steps:\n{steps_text}\n\nExpected: {tc.get('expected_result', '')}"
        return {
            "fields": {
                "project": {"key": self.project_key},
                "summary": f"[{tc.get('type', 'Functional')}] {tc.get('scenario', tc.get('tc_id', ''))}",
                "issuetype": {"name": self.issue_type},
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": description_text}]}],
                },
            }
        }


class TestRailExporter:
    def __init__(self):
        self.base_url = (config.TESTRAIL_URL or "").rstrip("/")
        self.auth = HTTPBasicAuth(config.TESTRAIL_EMAIL, config.TESTRAIL_API_KEY)
        self.project_id = config.TESTRAIL_PROJECT_ID
        self.suite_id = config.TESTRAIL_SUITE_ID

    def export(self, requirements, testcases):
        if not (self.base_url and config.TESTRAIL_EMAIL and config.TESTRAIL_API_KEY and self.project_id):
            raise RuntimeError("Thiếu cấu hình TestRail.")
        section_cache = {}
        created, failed = [], []
        for tc in testcases:
            module_name = tc.get("module") or tc.get("feature") or "General"
            try:
                section_id = self._get_or_create_section(module_name, section_cache)
                case_id = self._create_case(section_id, tc)
                created.append(case_id)
            except Exception as e:
                failed.append({"tc_id": tc.get("tc_id"), "error": str(e)})
        info(f"TestRail: đã tạo {len(created)}/{len(testcases)} case.")
        return {"created_case_ids": created, "failed": failed}

    def _get_or_create_section(self, name, cache):
        if name in cache:
            return cache[name]
        suite_qs = f"&suite_id={self.suite_id}" if self.suite_id else ""
        resp = requests.get(
            f"{self.base_url}/index.php?/api/v2/get_sections/{self.project_id}{suite_qs}",
            auth=self.auth,
            timeout=30,
        )
        resp.raise_for_status()
        sections = resp.json().get("sections", []) if isinstance(resp.json(), dict) else resp.json()
        for section in sections:
            if section.get("name") == name:
                cache[name] = section["id"]
                return section["id"]
        body = {"name": name}
        if self.suite_id:
            body["suite_id"] = self.suite_id
        resp = requests.post(
            f"{self.base_url}/index.php?/api/v2/add_section/{self.project_id}",
            json=body,
            auth=self.auth,
            timeout=30,
        )
        resp.raise_for_status()
        section_id = resp.json()["id"]
        cache[name] = section_id
        return section_id

    def _create_case(self, section_id, tc):
        steps = tc.get("steps") or []
        body = {
            "title": tc.get("scenario") or tc.get("tc_id") or "Untitled",
            "type_id": 1,
            "priority_id": {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}.get(tc.get("priority"), 2),
            "custom_preconds": tc.get('precondition', ''),
            "custom_steps": "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps)),
            "custom_expected": tc.get("expected_result", ""),
        }
        resp = requests.post(
            f"{self.base_url}/index.php?/api/v2/add_case/{section_id}",
            json=body,
            auth=self.auth,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["id"]


def export_json(requirements, testcases, use_cases=None, filename=None):
    timestamp = datetime.now().strftime(config.DATE_FORMAT)
    filename = filename or f"testcase_export_{timestamp}.json"
    filepath = config.OUTPUT_DIR / filename
    payload = {
        "generated_at": datetime.now().isoformat(),
        "use_cases": use_cases or [],
        "requirements": requirements,
        "testcases": testcases,
    }
    save_json(payload, filepath)
    info(f"Đã xuất JSON: {filepath}")
    return str(filepath)
