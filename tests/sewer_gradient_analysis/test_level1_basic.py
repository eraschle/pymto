"""
Level 1: Basic TDD Tests for Sewer Gradient Analysis

These tests represent the simplest scenarios and form the foundation
for Test-Driven Development of the sewer gradient correction system.

Following Red-Green-Refactor cycle:
1. RED: Write failing test
2. GREEN: Minimal implementation to pass
3. REFACTOR: Improve code quality
"""

import pytest
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from test_data_generator import (
    SewerTestDataGenerator, 
    SewerScenario, 
    SewerPipeline, 
    Point3D,
    Manhole
)

# TODO: These classes will be implemented in the main codebase
# For now, they're placeholders for TDD

@dataclass
class GradientCorrection:
    """Represents a correction made to a pipeline gradient."""
    pipeline_id: str
    original_points: List[Point3D]
    corrected_points: List[Point3D]
    correction_reason: str
    gradient_before: float
    gradient_after: float


class CorrectionType(Enum):
    NONE_NEEDED = "none"
    UPHILL_FIX = "uphill_fix"
    INSUFFICIENT_GRADIENT = "insufficient_gradient"
    GRADIENT_SMOOTHING = "gradient_smoothing"


class SewerGradientAnalyzer:
    """
    Main class for analyzing and correcting sewer pipeline gradients.
    
    This is the class we'll develop using TDD.
    """
    
    def __init__(self, min_gradient_percent: float = 0.5):
        self.min_gradient_percent = min_gradient_percent
        
    def analyze_scenario(self, scenario: SewerScenario) -> List[GradientCorrection]:
        """
        Analyze a complete sewer scenario and return necessary corrections.
        
        Args:
            scenario: SewerScenario containing manholes and pipelines
            
        Returns:
            List of corrections needed (empty if no corrections required)
        """
        # TODO: Implement this method
        raise NotImplementedError("TDD: Implement analyze_scenario method")
    
    def correct_pipeline_gradients(self, pipeline: SewerPipeline, 
                                 start_manhole: Optional[Manhole] = None,
                                 end_manhole: Optional[Manhole] = None) -> Optional[GradientCorrection]:
        """
        Correct gradients for a single pipeline.
        
        Args:
            pipeline: Pipeline to analyze and potentially correct
            start_manhole: Optional starting manhole constraint
            end_manhole: Optional ending manhole constraint
            
        Returns:
            GradientCorrection if changes needed, None otherwise
        """
        # TODO: Implement this method
        raise NotImplementedError("TDD: Implement correct_pipeline_gradients method")
    
    def detect_gradient_issues(self, pipeline: SewerPipeline) -> List[str]:
        """
        Detect gradient issues in a pipeline.
        
        Args:
            pipeline: Pipeline to analyze
            
        Returns:
            List of issue descriptions
        """
        # TODO: Implement this method  
        raise NotImplementedError("TDD: Implement detect_gradient_issues method")


class TestLevel1BasicScenarios:
    """Level 1: Basic TDD tests for sewer gradient analysis."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer with standard settings."""
        return SewerGradientAnalyzer(min_gradient_percent=0.5)
    
    @pytest.fixture
    def basic_scenarios(self):
        """Get basic test scenarios."""
        return SewerTestDataGenerator.create_basic_scenarios()
    
    def test_perfect_downhill_pipeline_needs_no_correction(self, analyzer, basic_scenarios):
        """
        RED TEST: Perfect downhill pipeline should need no corrections.
        
        This test will initially fail because analyze_scenario is not implemented.
        """
        # Find the perfect downhill scenario
        perfect_scenario = next(s for s in basic_scenarios if s.name == "perfect_downhill")
        
        # Analyze the scenario
        corrections = analyzer.analyze_scenario(perfect_scenario)
        
        # Should need no corrections
        assert len(corrections) == 0, "Perfect downhill pipeline should need no corrections"
        assert perfect_scenario.expected_corrections == 0, "Scenario expects no corrections"
    
    def test_simple_uphill_error_detection(self, analyzer, basic_scenarios):
        """
        RED TEST: Pipeline flowing uphill should be detected as problematic.
        """
        uphill_scenario = next(s for s in basic_scenarios if s.name == "simple_uphill_error")
        
        # Get the problematic pipeline
        problem_pipeline = uphill_scenario.pipelines[0]
        
        # Detect issues
        issues = analyzer.detect_gradient_issues(problem_pipeline)
        
        # Should detect uphill flow
        assert len(issues) > 0, "Should detect issues in uphill pipeline"
        assert any("uphill" in issue.lower() for issue in issues), "Should specifically detect uphill flow"
        
        # Verify test data expectation
        assert "uphill_flow" in problem_pipeline.expected_issues
    
    def test_simple_uphill_correction(self, analyzer, basic_scenarios):
        """
        RED TEST: Uphill pipeline should be corrected to flow downhill.
        """
        uphill_scenario = next(s for s in basic_scenarios if s.name == "simple_uphill_error")
        problem_pipeline = uphill_scenario.pipelines[0]
        
        # Get manholes for constraints
        start_manhole = uphill_scenario.manholes[0]
        end_manhole = uphill_scenario.manholes[1]
        
        # Correct the pipeline
        correction = analyzer.correct_pipeline_gradients(
            problem_pipeline, start_manhole, end_manhole
        )
        
        # Should have a correction
        assert correction is not None, "Uphill pipeline should need correction"
        assert correction.correction_reason == CorrectionType.UPHILL_FIX.value
        
        # Corrected pipeline should flow downhill
        corrected_gradients = self._calculate_gradients(correction.corrected_points)
        assert all(grad <= 0 for grad in corrected_gradients), "All gradients should be downhill (≤ 0)"
        
        # Should meet minimum gradient requirement
        assert all(abs(grad) >= analyzer.min_gradient_percent for grad in corrected_gradients), \
            f"All gradients should meet minimum {analyzer.min_gradient_percent}% requirement"
    
    def test_insufficient_gradient_detection(self, analyzer, basic_scenarios):
        """
        RED TEST: Pipeline with insufficient gradient should be detected.
        """
        insufficient_scenario = next(s for s in basic_scenarios if s.name == "insufficient_gradient")
        problem_pipeline = insufficient_scenario.pipelines[0]
        
        # Detect issues
        issues = analyzer.detect_gradient_issues(problem_pipeline)
        
        # Should detect insufficient gradient
        assert len(issues) > 0, "Should detect insufficient gradient"
        assert any("insufficient" in issue.lower() or "shallow" in issue.lower() 
                  for issue in issues), "Should detect insufficient/shallow gradient"
    
    def test_insufficient_gradient_correction(self, analyzer, basic_scenarios):
        """
        RED TEST: Pipeline with insufficient gradient should be corrected.
        """
        insufficient_scenario = next(s for s in basic_scenarios if s.name == "insufficient_gradient")
        problem_pipeline = insufficient_scenario.pipelines[0]
        
        start_manhole = insufficient_scenario.manholes[0]
        end_manhole = insufficient_scenario.manholes[1]
        
        # Correct the pipeline
        correction = analyzer.correct_pipeline_gradients(
            problem_pipeline, start_manhole, end_manhole
        )
        
        # Should have a correction
        assert correction is not None, "Insufficient gradient should need correction"
        
        # Corrected gradients should meet minimum requirement
        corrected_gradients = self._calculate_gradients(correction.corrected_points)
        assert all(abs(grad) >= analyzer.min_gradient_percent for grad in corrected_gradients), \
            f"Corrected gradients should meet minimum {analyzer.min_gradient_percent}% requirement"
        
        # Should still flow downhill
        assert all(grad <= 0 for grad in corrected_gradients), "Should maintain downhill flow"
    
    def test_manhole_constraint_adherence(self, analyzer, basic_scenarios):
        """
        RED TEST: Corrections should respect manhole invert elevations.
        """
        # Use any scenario with manholes
        scenario = basic_scenarios[0]  # Perfect downhill has manholes
        pipeline = scenario.pipelines[0]
        
        start_manhole = scenario.manholes[0]
        end_manhole = scenario.manholes[1] 
        
        # Correct pipeline (may or may not need correction)
        correction = analyzer.correct_pipeline_gradients(
            pipeline, start_manhole, end_manhole
        )
        
        # If correction was made, check constraints
        if correction:
            corrected_points = correction.corrected_points
            
            # Start point should match start manhole invert elevation
            assert abs(corrected_points[0].z - start_manhole.invert_elevation) < 0.01, \
                "Corrected start should match start manhole invert"
            
            # End point should match end manhole invert elevation  
            assert abs(corrected_points[-1].z - end_manhole.invert_elevation) < 0.01, \
                "Corrected end should match end manhole invert"
    
    def test_gradient_calculation_accuracy(self, analyzer):
        """
        RED TEST: Gradient calculations should be mathematically correct.
        """
        # Create simple test pipeline
        test_points = [
            Point3D(0, 0, 100.0),    # Start
            Point3D(50, 0, 99.0),    # 2% downhill gradient
            Point3D(100, 0, 97.0)    # 4% downhill gradient
        ]
        
        gradients = self._calculate_gradients(test_points)
        
        # Check gradient calculations
        assert abs(gradients[0] - (-2.0)) < 0.01, "First segment should be -2.0% gradient"
        assert abs(gradients[1] - (-4.0)) < 0.01, "Second segment should be -4.0% gradient"
    
    # Helper methods
    def _calculate_gradients(self, points: List[Point3D]) -> List[float]:
        """Calculate gradients between consecutive points."""
        gradients = []
        for i in range(len(points) - 1):
            start, end = points[i], points[i + 1]
            distance = start.distance_2d(end)
            if distance > 0:
                elevation_diff = end.z - start.z
                gradient_percent = (elevation_diff / distance) * 100
                gradients.append(gradient_percent)
            else:
                gradients.append(0.0)
        return gradients


class TestTDDWorkflow:
    """Tests to verify TDD workflow and test data integrity."""
    
    def test_all_basic_scenarios_load_correctly(self):
        """Verify all basic scenarios are properly structured."""
        scenarios = SewerTestDataGenerator.create_basic_scenarios()
        
        assert len(scenarios) >= 3, "Should have at least 3 basic scenarios"
        
        for scenario in scenarios:
            # Each scenario should have required attributes
            assert scenario.name, "Scenario should have a name"
            assert scenario.description, "Scenario should have description"
            assert len(scenario.manholes) >= 2, "Scenario should have at least 2 manholes"
            assert len(scenario.pipelines) >= 1, "Scenario should have at least 1 pipeline"
            
            # Pipelines should have valid points
            for pipeline in scenario.pipelines:
                assert len(pipeline.points) >= 2, "Pipeline should have at least 2 points"
                assert pipeline.expected_issues is not None, "Pipeline should have expected_issues list"
    
    def test_scenario_complexity_classification(self):
        """Verify scenarios are correctly classified by complexity."""
        scenarios = SewerTestDataGenerator.create_basic_scenarios()
        
        for scenario in scenarios:
            assert scenario.complexity.value == "basic", "All scenarios should be classified as basic"
    
    def test_visualization_data_generation(self):
        """Test that visualization data can be generated without errors."""
        scenarios = SewerTestDataGenerator.create_basic_scenarios()
        
        # Test gradient calculation for visualization
        for scenario in scenarios:
            for pipeline in scenario.pipelines:
                gradients = pipeline.get_gradients()
                
                # Should have one less gradient than points
                assert len(gradients) == len(pipeline.points) - 1, \
                    "Should have n-1 gradients for n points"
                
                # Gradients should be numeric
                for gradient in gradients:
                    assert isinstance(gradient, (int, float)), "Gradient should be numeric"


# Running instructions for TDD:
"""
To run these tests in TDD fashion:

1. Run tests first (they should all FAIL - RED phase):
   pytest tests/sewer_gradient_analysis/test_level1_basic.py -v

2. Implement minimal code to make first test pass (GREEN phase)

3. Refactor and improve (REFACTOR phase)

4. Move to next failing test and repeat

Example TDD cycle:
1. RED: test_perfect_downhill_pipeline_needs_no_correction fails
2. GREEN: Implement basic analyze_scenario that returns empty list
3. REFACTOR: Clean up code structure
4. RED: test_simple_uphill_error_detection fails  
5. GREEN: Implement basic detect_gradient_issues
6. Continue...
"""