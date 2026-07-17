from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Requirement:
    """Một yêu cầu nghiệp vụ - đầu ra của Feature Extraction."""
    req_id: str = ""
    feature: str = ""
    module: str = ""
    description: str = ""
    business_rules: List[str] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)
    priority: str = "Medium"
    risk: str = ""
    elements: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self):
        return {
            "req_id": self.req_id,
            "feature": self.feature,
            "module": self.module,
            "description": self.description,
            "business_rules": self.business_rules,
            "validation_rules": self.validation_rules,
            "priority": self.priority,
            "risk": self.risk,
            "elements": self.elements,
        }


@dataclass
class UseCase:
    """Use Case ở mức nghiệp vụ."""
    uc_id: str = ""
    title: str = ""
    actor: str = "Người dùng"
    module: str = ""
    description: str = ""
    preconditions: List[str] = field(default_factory=list)
    main_flow: List[str] = field(default_factory=list)
    alternative_flows: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    related_features: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "uc_id": self.uc_id,
            "title": self.title,
            "actor": self.actor,
            "module": self.module,
            "description": self.description,
            "preconditions": self.preconditions,
            "main_flow": self.main_flow,
            "alternative_flows": self.alternative_flows,
            "postconditions": self.postconditions,
            "related_features": self.related_features,
        }


@dataclass
class TestCase:
    """Test Case."""
    tc_id: str = ""
    feature: str = ""
    module: str = ""
    scenario: str = ""
    type: str = "Functional"
    priority: str = "Medium"
    severity: str = "Medium"
    precondition: str = ""
    test_data: str = ""
    steps: List[str] = field(default_factory=list)
    expected_result: str = ""
    requirement_id: str = ""
    tags: List[str] = field(default_factory=list)
    element_ref: str = ""

    def to_dict(self):
        return {
            "tc_id": self.tc_id,
            "feature": self.feature,
            "module": self.module,
            "scenario": self.scenario,
            "type": self.type,
            "priority": self.priority,
            "severity": self.severity,
            "precondition": self.precondition,
            "test_data": self.test_data,
            "steps": self.steps,
            "expected_result": self.expected_result,
            "requirement_id": self.requirement_id,
            "tags": self.tags,
            "element_ref": self.element_ref,
        }
