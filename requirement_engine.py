from llm_service import LLMService
from models import Requirement
from utils import info, warning


class RequirementEngine:
    def __init__(self, llm=None):
        self.llm = llm or LLMService()

    def infer(self, extracted_features, website_type="General"):
        info("Requirement Inference: calling LLM to analyze features...")
        extracted_features = extracted_features or []

        try:
            analyzed = self.llm.analyze_requirements(extracted_features)
        except Exception as e:
            warning(f"LLM analyze_requirements thất bại: {e}. Dùng features gốc.")
            analyzed = []

        if not isinstance(analyzed, list) or not analyzed:
            warning("LLM không trả về danh sách hợp lệ, dùng thẳng kết quả Feature Extraction.")
            return extracted_features

        base_by_id = {f.get("req_id", ""): f for f in extracted_features if f.get("req_id")}
        base_by_feature = {f.get("feature", ""): f for f in extracted_features}

        normalized = []
        dropped_hallucinated = 0
        for item in analyzed:
            if not isinstance(item, dict):
                continue

            req_id = str(item.get("req_id") or "").strip()
            base = base_by_id.get(req_id)

            if base is None:
                feature_name = item.get("feature") or "Unknown"
                base = base_by_feature.get(feature_name)

            if base is None:
                dropped_hallucinated += 1
                continue

            feature_name = base.get("feature") or item.get("feature") or "Unknown"
            req = Requirement(
                req_id=base.get("req_id", ""),
                feature=feature_name,
                module=base.get("module") or item.get("module") or website_type.upper(),
                description=item.get("description") or base.get("description") or f"Yêu cầu cho {feature_name}.",
                business_rules=item.get("business_rules") or base.get("business_rules") or [],
                validation_rules=item.get("validation_rules") or base.get("validation_rules") or [],
                priority=item.get("priority") or base.get("priority") or "Medium",
                risk=item.get("risk", ""),
                elements=base.get("elements") or [],
            )
            normalized.append(req.to_dict())

        if dropped_hallucinated:
            warning(f"Đã loại {dropped_hallucinated} requirement không khớp req_id/feature nào.")

        covered_ids = {r["req_id"] for r in normalized if r.get("req_id")}
        for req_id, base in base_by_id.items():
            if req_id not in covered_ids:
                normalized.append(base)

        return normalized
