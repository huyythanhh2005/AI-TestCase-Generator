from llm_service import LLMService
from models import UseCase
from utils import info, warning


class UseCaseEngine:
    def __init__(self, llm=None):
        self.llm = llm or LLMService()

    def infer(self, requirements, website_type="General"):
        if not requirements:
            return []

        info("Use Case Synthesis...")
        usecases = []
        total = len(requirements)

        for index, req in enumerate(requirements, start=1):
            feature = req.get("feature", "")
            module = req.get("module", "General")
            info(f"Requirement {index}/{total}: {feature}")

            try:
                raw = self.llm.generate_use_cases(
                    website_type=website_type,
                    module=module,
                    requirements=[req],
                    min_uc=1,
                    max_uc=1,
                )
            except Exception as e:
                warning(str(e))
                continue

            usecases.extend(self._normalize(raw, req))

        self._remove_duplicate(usecases)
        for i, uc in enumerate(usecases, 1):
            uc["uc_id"] = f"UC{i:04d}"

        info(f"Tổng hợp {len(usecases)} use case.")
        return usecases

    def _normalize(self, raw_items, requirement):
        result = []
        feature = requirement.get("feature")
        for item in raw_items or []:
            if not isinstance(item, dict):
                continue
            uc = UseCase(
                title=item.get("title", feature),
                actor=item.get("actor", "User"),
                module=requirement.get("module", "General"),
                description=item.get("description", ""),
                preconditions=item.get("preconditions", []),
                main_flow=item.get("main_flow", []),
                alternative_flows=item.get("alternative_flows", []),
                postconditions=item.get("postconditions", []),
                related_features=[feature],
            )
            result.append(uc.to_dict())
        return result

    def _remove_duplicate(self, usecases):
        seen = set()
        result = []
        for uc in usecases:
            key = (uc["title"].lower().strip(), tuple(uc["related_features"]))
            if key in seen:
                continue
            seen.add(key)
            result.append(uc)
        usecases.clear()
        usecases.extend(result)
