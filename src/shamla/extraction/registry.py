import importlib.util
import os
import re
from dataclasses import dataclass
from typing import Callable, Union, Dict, List

@dataclass
class Department:
    name: str
    patterns: List[Union[str, re.Pattern]]
    extractor: Callable[[str], List[str]] | None = None

class ExtractionRegistry:
    def __init__(self):
        self._departments: Dict[str, Department] = {}

    def register_department(
        self,
        name: str,
        patterns: List[Union[str, re.Pattern]] | None = None,
        extractor: Callable[[str], List[str]] | None = None
    ) -> None:
        """Register a custom citation extraction department."""
        if not name:
            raise ValueError("Department name cannot be empty")
        
        compiled_patterns = []
        if patterns:
            for p in patterns:
                if isinstance(p, str):
                    compiled_patterns.append(re.compile(p))
                else:
                    compiled_patterns.append(p)
                    
        self._departments[name] = Department(
            name=name,
            patterns=compiled_patterns,
            extractor=extractor
        )

    def get_departments(self) -> Dict[str, Department]:
        """Get all registered departments."""
        return self._departments

    def clear(self) -> None:
        """Clear all registered departments."""
        self._departments.clear()

# Global registry instance
global_registry = ExtractionRegistry()

def register_department(
    name: str,
    patterns: List[Union[str, re.Pattern]] | None = None,
    extractor: Callable[[str], List[str]] | None = None
) -> None:
    global_registry.register_department(name, patterns, extractor)

def department(name: str, patterns: List[Union[str, re.Pattern]] | None = None):
    """Decorator to register a custom extractor function under a department name."""
    def decorator(func: Callable[[str], List[str]]):
        global_registry.register_department(name, patterns=patterns, extractor=func)
        return func
    return decorator

def load_extractors_from_file(filepath: str) -> None:
    """Load a Python module from a file path dynamically to trigger registrations."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    module_name = os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for: {filepath}")
        
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
