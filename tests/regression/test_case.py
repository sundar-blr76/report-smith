"""
Regression Testing Framework for ReportSmith

This module provides data structures for test cases and golden snapshots.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml
import json
from datetime import datetime


@dataclass
class TestCase:
    """Represents a regression test case."""
    
    id: str
    description: str
    question: str
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    expectations: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'TestCase':
        """Load test case from YAML file."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, yaml_path: Path) -> None:
        """Save test case to YAML file."""
        with open(yaml_path, 'w') as f:
            yaml.dump(asdict(self), f, default_flow_style=False, sort_keys=False)


@dataclass
class GoldenSnapshot:
    """Represents a golden snapshot of expected behavior."""
    
    test_id: str
    question: str
    timestamp: str
    response: Dict[str, Any]
    
    @classmethod
    def from_json(cls, json_path: Path) -> 'GoldenSnapshot':
        """Load golden snapshot from JSON file."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_json(self, json_path: Path) -> None:
        """Save golden snapshot to JSON file."""
        with open(json_path, 'w') as f:
            json.dump(asdict(self), f, indent=2, default=str)
    
    @classmethod
    def from_api_response(cls, test_id: str, question: str, response: Dict[str, Any]) -> 'GoldenSnapshot':
        """Create golden snapshot from API response."""
        return cls(
            test_id=test_id,
            question=question,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            response=response
        )


@dataclass
class ComparisonResult:
    """Result of comparing actual vs golden snapshot."""
    
    test_id: str
    passed: bool
    differences: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_difference(self, category: str, expected: Any, actual: Any, path: str = ""):
        """Add a difference to the result."""
        self.differences.append({
            "category": category,
            "path": path,
            "expected": expected,
            "actual": actual
        })
        self.passed = False
    
    def add_warning(self, message: str):
        """Add a warning to the result."""
        self.warnings.append(message)
