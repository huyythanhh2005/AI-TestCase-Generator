from collections import defaultdict
from bs4 import BeautifulSoup
from models import Requirement
from utils import info


class FeatureExtractor:
    def __init__(self):
        self.result = []
        self.modules = defaultdict(list)

    def extract(self, page_data):
        info("Feature Extraction: analyzing page data...")
        soup = BeautifulSoup(page_data.get("html", ""), "html.parser")

        self._extract_forms(page_data)
        self._extract_inputs(page_data)
        self._extract_selects(page_data)
        self._extract_buttons(page_data)
        self._extract_links(page_data)
        self._extract_tables(page_data)
        self._extract_images(page_data)
        self._extract_metadata(page_data)
        self._extract_api(page_data)
        self._extract_storage(page_data)

        self._remove_duplicates()
        return [r.to_dict() for r in self.result]

    def _add(self, feature, module, description, business_rules=None, validation_rules=None, priority="Medium", elements=None):
        self.result.append(
            Requirement(
                req_id=f"F{len(self.result) + 1:04d}",
                feature=feature,
                module=module,
                description=description,
                business_rules=business_rules or [],
                validation_rules=validation_rules or [],
                priority=priority,
                elements=elements or [],
            )
        )

    def _extract_forms(self, data):
        for form in data.get("forms", []):
            method = form.get("method", "GET")
            desc = f"Form với {form.get('input_count', 0)} input(s), method={method}"
            self._add(
                "Form",
                "Input",
                desc,
                ["Tất cả trường bắt buộc phải điền"],
                ["Dữ liệu không hợp lệ phải bị từ chối"],
                "High",
                elements=[form],
            )

    def _extract_inputs(self, data):
        inputs = [inp for inp in data.get("inputs", []) if inp.get("type", "").lower() != "hidden"]
        if not inputs:
            return
        self._add(
            "Text Input",
            "Input",
            f"{len(inputs)} text input(s)",
            ["Input phải chấp nhận dữ liệu hợp lệ"],
            ["Input phải validate đúng"],
            "High",
            elements=inputs,
        )

    def _extract_selects(self, data):
        selects = data.get("selects", [])
        if not selects:
            return
        self._add(
            "Select/Dropdown",
            "Input",
            f"{len(selects)} select element(s)",
            ["Select phải có các option hợp lệ"],
            ["Option mặc định phải rõ ràng"],
            "High",
            elements=selects,
        )

    def _extract_buttons(self, data):
        for btn in data.get("buttons", []):
            text = (btn.get("text") or "").strip() or "Button"
            self._add(
                text,
                "Button",
                f"Button '{text}' phải hoạt động đúng",
                ["Button phải thực thi hành động đúng"],
                ["Button phải clickable"],
                "High",
                elements=[btn],
            )

    def _extract_links(self, data):
        for link in data.get("links", []):
            href = link.get("href", "")
            if not href:
                continue
            text = (link.get("text") or "").strip() or "Link"
            self._add(
                text,
                "Navigation",
                f"Điều hướng tới {href}",
                ["Điều hướng phải chính xác"],
                ["404 page không được phép"],
                "Medium",
                elements=[link],
            )

    def _extract_tables(self, data):
        for idx, table in enumerate(data.get("tables", []), start=1):
            rows = table.get("row_count", 0)
            cols = table.get("column_count", 0)
            self._add(
                f"Table {idx}",
                "Table",
                f"Hiển thị {rows} dòng và {cols} cột",
                ["Dữ liệu bảng phải hiển thị đúng"],
                ["Không được thiếu dòng"],
                "Medium",
                elements=[table],
            )

    def _extract_images(self, data):
        if not data.get("images"):
            return
        images = data.get("images", [])
        missing_alt = sum(1 for img in images if not img.get("alt"))
        self._add(
            "Image Display",
            "Media",
            f"{len(images)} image(s) phải hiển thị đúng",
            ["Tất cả image phải load thành công"],
            [f"{missing_alt} image(s) thiếu alt text"],
            "Low",
            elements=images[:30],
        )

    def _extract_metadata(self, data):
        metadata = data.get("metadata", {}) or {}
        if metadata.get("title"):
            self._add(
                "Page Title",
                "SEO",
                metadata["title"],
                ["Mỗi trang phải có title duy nhất"],
                ["Title không được để trống"],
                "Low",
            )

    def _extract_api(self, data):
        found = set()
        for item in data.get("network", []):
            url = item.get("url", "")
            method = item.get("method", "GET")
            if not url or url in found:
                continue
            found.add(url)
            if item.get("resource_type") not in ("xhr", "fetch"):
                continue
            self._add(
                "API",
                "Backend",
                f"{method} {url}",
                ["API phải trả kết quả đúng"],
                ["HTTP status phải hợp lệ"],
                "High",
                elements=[{"url": url, "method": method}],
            )

    def _extract_storage(self, data):
        if data.get("cookies"):
            self._add(
                "Cookie",
                "Browser",
                "Cookie handling",
                ["Cookie phải được lưu đúng"],
                ["Session cookie phải hợp lệ"],
                "Medium",
            )

    def _remove_duplicates(self):
        unique, seen = [], set()
        for req in self.result:
            key = (req.feature.lower(), req.module.lower())
            if key in seen:
                continue
            seen.add(key)
            unique.append(req)
        self.result = unique


def run(page_data):
    return FeatureExtractor().extract(page_data)
