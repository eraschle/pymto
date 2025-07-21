"""
Test Data Generator for Sewer Gradient Analysis

Creates realistic test scenarios with different complexity levels
and provides visualization capabilities.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import math


class ScenarioComplexity(Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate" 
    COMPLEX = "complex"
    REAL_WORLD = "real_world"


@dataclass
class Point3D:
    """3D Point representation for sewer pipeline analysis."""
    x: float  # East coordinate (m)
    y: float  # North coordinate (m) 
    z: float  # Altitude (m)
    
    def distance_2d(self, other: 'Point3D') -> float:
        """Calculate 2D distance to another point."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)


@dataclass
class Manhole:
    """Represents a manhole/shaft in the sewer system."""
    id: str
    location: Point3D
    invert_elevation: float  # Bottom of manhole (where pipes connect)
    
    @property
    def cover_elevation(self) -> float:
        """Surface elevation of manhole cover."""
        return self.location.z


@dataclass  
class SewerPipeline:
    """Represents a sewer pipeline with potential gradient issues."""
    id: str
    points: List[Point3D]
    start_manhole: Optional[Manhole] = None
    end_manhole: Optional[Manhole] = None
    expected_issues: List[str] = None  # For testing validation
    
    def __post_init__(self):
        if self.expected_issues is None:
            self.expected_issues = []
    
    def get_gradients(self) -> List[float]:
        """Calculate gradients between consecutive points (%)."""
        gradients = []
        for i in range(len(self.points) - 1):
            start, end = self.points[i], self.points[i + 1]
            distance = start.distance_2d(end)
            if distance > 0:
                elevation_diff = end.z - start.z
                gradient_percent = (elevation_diff / distance) * 100
                gradients.append(gradient_percent)
            else:
                gradients.append(0.0)
        return gradients


@dataclass
class SewerScenario:
    """Complete test scenario with manholes and pipelines."""
    name: str
    description: str
    complexity: ScenarioComplexity
    manholes: List[Manhole]
    pipelines: List[SewerPipeline]
    expected_corrections: int = 0  # Number of expected corrections


class SewerTestDataGenerator:
    """Generates realistic sewer system test data."""
    
    @staticmethod
    def create_basic_scenarios() -> List[SewerScenario]:
        """Level 1: Basic scenarios for initial TDD development."""
        scenarios = []
        
        # Scenario 1.1: Perfect downhill pipeline
        scenarios.append(SewerScenario(
            name="perfect_downhill",
            description="Simple pipeline with consistent 2% downhill gradient",
            complexity=ScenarioComplexity.BASIC,
            manholes=[
                Manhole("MH1", Point3D(0, 0, 100.0), 99.5),
                Manhole("MH2", Point3D(100, 0, 98.0), 97.5)
            ],
            pipelines=[
                SewerPipeline(
                    id="PIPE1",
                    points=[
                        Point3D(0, 0, 99.5),   # Start at MH1 invert
                        Point3D(100, 0, 97.5)  # End at MH2 invert
                    ],
                    expected_issues=[]  # No issues expected
                )
            ],
            expected_corrections=0
        ))
        
        # Scenario 1.2: Simple uphill error
        scenarios.append(SewerScenario(
            name="simple_uphill_error", 
            description="Pipeline incorrectly flowing uphill - needs correction",
            complexity=ScenarioComplexity.BASIC,
            manholes=[
                Manhole("MH1", Point3D(0, 0, 100.0), 99.5),
                Manhole("MH2", Point3D(50, 0, 102.0), 101.5)  # Higher manhole
            ],
            pipelines=[
                SewerPipeline(
                    id="PIPE1", 
                    points=[
                        Point3D(0, 0, 99.5),   # Start at MH1
                        Point3D(50, 0, 101.5)  # Flowing uphill to MH2 - ERROR!
                    ],
                    expected_issues=["uphill_flow"]
                )
            ],
            expected_corrections=1
        ))
        
        # Scenario 1.3: Insufficient gradient
        scenarios.append(SewerScenario(
            name="insufficient_gradient",
            description="Pipeline with gradient too shallow (0.1% instead of min 0.5%)",
            complexity=ScenarioComplexity.BASIC,
            manholes=[
                Manhole("MH1", Point3D(0, 0, 100.0), 99.5),
                Manhole("MH2", Point3D(200, 0, 99.8), 99.3)
            ],
            pipelines=[
                SewerPipeline(
                    id="PIPE1",
                    points=[
                        Point3D(0, 0, 99.5),
                        Point3D(200, 0, 99.3)  # Only 0.1% gradient
                    ],
                    expected_issues=["insufficient_gradient"]
                )
            ],
            expected_corrections=1
        ))
        
        return scenarios
    
    @staticmethod
    def create_intermediate_scenarios() -> List[SewerScenario]:
        """Level 2: Intermediate scenarios with gradient breaks."""
        scenarios = []
        
        # Scenario 2.1: Legitimate gradient break (drop structure)
        scenarios.append(SewerScenario(
            name="legitimate_gradient_break",
            description="Pipeline with intentional steep section (drop structure)",
            complexity=ScenarioComplexity.INTERMEDIATE,
            manholes=[
                Manhole("MH1", Point3D(0, 0, 100.0), 99.5),
                Manhole("MH2", Point3D(100, 0, 95.0), 94.5)
            ],
            pipelines=[
                SewerPipeline(
                    id="PIPE1",
                    points=[
                        Point3D(0, 0, 99.5),    # Start
                        Point3D(40, 0, 98.7),   # Normal 2% gradient
                        Point3D(50, 0, 96.0),   # Steep drop (27% gradient!)
                        Point3D(100, 0, 94.5)   # Return to normal 3% gradient
                    ],
                    expected_issues=[]  # This is intentional design
                )
            ],
            expected_corrections=0  # Should preserve the gradient break
        ))
        
        # Scenario 2.2: Mixed uphill/downhill with corrections needed
        scenarios.append(SewerScenario(
            name="mixed_uphill_downhill",
            description="Pipeline with multiple uphill sections needing correction",
            complexity=ScenarioComplexity.INTERMEDIATE,
            manholes=[
                Manhole("MH1", Point3D(0, 0, 100.0), 99.5),
                Manhole("MH2", Point3D(100, 0, 98.0), 97.5)
            ],
            pipelines=[
                SewerPipeline(
                    id="PIPE1",
                    points=[
                        Point3D(0, 0, 99.5),    # Start at MH1
                        Point3D(20, 0, 99.1),   # Downhill OK
                        Point3D(40, 0, 99.3),   # Uphill ERROR
                        Point3D(60, 0, 98.9),   # Downhill OK  
                        Point3D(80, 0, 99.1),   # Uphill ERROR
                        Point3D(100, 0, 97.5)   # End at MH2
                    ],
                    expected_issues=["uphill_segments_at_40m", "uphill_segments_at_80m"]
                )
            ],
            expected_corrections=1  # Should smooth the entire profile
        ))
        
        return scenarios
    
    @staticmethod 
    def create_complex_scenarios() -> List[SewerScenario]:
        """Level 3: Complex scenarios with multiple issues."""
        scenarios = []
        
        # Scenario 3.1: Long pipeline with multiple gradient breaks
        scenarios.append(SewerScenario(
            name="multiple_gradient_breaks",
            description="Long sewer line with multiple legitimate and problematic sections",
            complexity=ScenarioComplexity.COMPLEX,
            manholes=[
                Manhole("MH1", Point3D(0, 0, 105.0), 104.5),
                Manhole("MH2", Point3D(80, 0, 102.0), 101.5),   # Intermediate  
                Manhole("MH3", Point3D(200, 0, 98.0), 97.5)     # Final
            ],
            pipelines=[
                SewerPipeline(
                    id="PIPE1",
                    points=[
                        Point3D(0, 0, 104.5),    # Start at MH1
                        Point3D(20, 0, 103.9),   # Normal 3% gradient  
                        Point3D(30, 0, 102.5),   # Steep drop (14% - legitimate?)
                        Point3D(50, 0, 102.1),   # Normal 2% gradient
                        Point3D(60, 0, 102.3),   # Uphill ERROR
                        Point3D(80, 0, 101.5)    # End at MH2
                    ],
                    expected_issues=["steep_section_at_30m", "uphill_at_60m"]
                ),
                SewerPipeline(
                    id="PIPE2", 
                    points=[
                        Point3D(80, 0, 101.5),   # Start at MH2
                        Point3D(120, 0, 100.3),  # Normal 3% gradient
                        Point3D(160, 0, 98.9),   # Normal 3.5% gradient  
                        Point3D(200, 0, 97.5)    # End at MH3
                    ],
                    expected_issues=[]
                )
            ],
            expected_corrections=1
        ))
        
        return scenarios
    
    @staticmethod
    def create_real_world_scenarios() -> List[SewerScenario]:
        """Level 4: Real-world complex scenarios."""
        scenarios = []
        
        # Scenario 4.1: Realistic urban sewer with terrain challenges
        scenarios.append(SewerScenario(
            name="urban_terrain_challenge",
            description="Real-world scenario with terrain constraints and multiple issues",
            complexity=ScenarioComplexity.REAL_WORLD,
            manholes=[
                Manhole("MH_START", Point3D(0, 0, 108.2), 107.5),
                Manhole("MH_MID1", Point3D(75, 15, 105.8), 105.0),
                Manhole("MH_MID2", Point3D(150, -10, 103.2), 102.5),
                Manhole("MH_END", Point3D(220, 5, 100.5), 99.8)
            ],
            pipelines=[
                SewerPipeline(
                    id="MAIN_TRUNK",
                    points=[
                        Point3D(0, 0, 107.5),      # Start  
                        Point3D(15, 3, 107.0),     # Normal descent
                        Point3D(35, 8, 106.8),     # Too shallow
                        Point3D(55, 12, 106.2),    # Good gradient
                        Point3D(75, 15, 105.0),    # Reach MH_MID1
                        Point3D(95, 10, 104.6),    # Continue descent
                        Point3D(115, 0, 104.1),    # Good
                        Point3D(130, -5, 103.8),   # Shallow again
                        Point3D(150, -10, 102.5),  # Reach MH_MID2
                        Point3D(170, -7, 102.2),   # Normal
                        Point3D(190, -2, 101.5),   # Good gradient
                        Point3D(210, 2, 100.8),    # Approaching end
                        Point3D(220, 5, 99.8)      # End at MH_END
                    ],
                    expected_issues=["shallow_gradient_at_35m", "shallow_gradient_at_130m"]
                )
            ],
            expected_corrections=1
        ))
        
        return scenarios

    @staticmethod
    def visualize_scenario(scenario: SewerScenario, save_path: Optional[str] = None):
        """
        Create a text-based visualization of the sewer scenario.
        For matplotlib plots, use the separate visualization module.
        """
        # Import here to avoid circular dependency
        from ascii_visualizer import ASCIISewerVisualizer
        return ASCIISewerVisualizer.create_profile_diagram(scenario)


def generate_all_test_scenarios() -> List[SewerScenario]:
    """Generate all test scenarios across all complexity levels."""
    generator = SewerTestDataGenerator()
    
    all_scenarios = []
    all_scenarios.extend(generator.create_basic_scenarios())
    all_scenarios.extend(generator.create_intermediate_scenarios())
    all_scenarios.extend(generator.create_complex_scenarios())
    all_scenarios.extend(generator.create_real_world_scenarios())
    
    return all_scenarios


if __name__ == "__main__":
    # Generate and visualize all scenarios  
    scenarios = generate_all_test_scenarios()
    
    print(f"Generated {len(scenarios)} test scenarios:")
    for scenario in scenarios:
        print(f"- {scenario.name} ({scenario.complexity.value}): {scenario.description}")
        
    print("\nFor detailed visualizations, run: python ascii_visualizer.py")