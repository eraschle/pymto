"""
Pytest configuration for sewer gradient analysis tests.

Provides common fixtures and test utilities.
"""

import pytest
from typing import List
from test_data_generator import (
    SewerTestDataGenerator, 
    SewerScenario, 
    generate_all_test_scenarios,
    ScenarioComplexity
)


@pytest.fixture(scope="session")
def all_test_scenarios() -> List[SewerScenario]:
    """Generate all test scenarios once per test session."""
    return generate_all_test_scenarios()


@pytest.fixture
def basic_scenarios(all_test_scenarios) -> List[SewerScenario]:
    """Get only basic complexity scenarios."""
    return [s for s in all_test_scenarios if s.complexity == ScenarioComplexity.BASIC]


@pytest.fixture 
def intermediate_scenarios(all_test_scenarios) -> List[SewerScenario]:
    """Get only intermediate complexity scenarios."""
    return [s for s in all_test_scenarios if s.complexity == ScenarioComplexity.INTERMEDIATE]


@pytest.fixture
def complex_scenarios(all_test_scenarios) -> List[SewerScenario]:
    """Get only complex scenarios.""" 
    return [s for s in all_test_scenarios if s.complexity == ScenarioComplexity.COMPLEX]


@pytest.fixture
def real_world_scenarios(all_test_scenarios) -> List[SewerScenario]:
    """Get only real-world scenarios."""
    return [s for s in all_test_scenarios if s.complexity == ScenarioComplexity.REAL_WORLD]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", 
        "basic: mark test as basic level (Level 1)"
    )
    config.addinivalue_line(
        "markers",
        "intermediate: mark test as intermediate level (Level 2)" 
    )
    config.addinivalue_line(
        "markers",
        "complex: mark test as complex level (Level 3)"
    )
    config.addinivalue_line(
        "markers", 
        "real_world: mark test as real-world level (Level 4)"
    )
    config.addinivalue_line(
        "markers",
        "tdd: mark test as part of TDD workflow"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on file names
        if "level1" in item.fspath.basename:
            item.add_marker(pytest.mark.basic)
        elif "level2" in item.fspath.basename:
            item.add_marker(pytest.mark.intermediate) 
        elif "level3" in item.fspath.basename:
            item.add_marker(pytest.mark.complex)
        elif "level4" in item.fspath.basename:
            item.add_marker(pytest.mark.real_world)
        
        # Add TDD marker to all tests in this directory
        item.add_marker(pytest.mark.tdd)