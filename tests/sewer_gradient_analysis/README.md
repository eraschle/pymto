# Sewer Gradient Analysis - TDD Test Suite

This directory contains a comprehensive Test-Driven Development (TDD) suite for analyzing and correcting sewer pipeline gradients.

## Overview

The sewer gradient analysis system is designed to:
1. **Detect gradient problems** in sewer pipelines (uphill flow, insufficient gradient)
2. **Preserve legitimate gradient breaks** (drop structures, intentional steep sections)
3. **Correct problematic gradients** while respecting manhole constraints
4. **Handle complex scenarios** with multiple segments and real-world constraints

## Test Structure

### Complexity Levels

#### Level 1: Basic Scenarios (`test_level1_basic.py`)
- ✅ **Perfect downhill pipeline** - No corrections needed
- ⚠️  **Simple uphill error** - Single pipeline flowing uphill 
- ⚠️  **Insufficient gradient** - Gradient too shallow (0.1% vs required 0.5%)

#### Level 2: Intermediate Scenarios (`test_level2_intermediate.py`) 
- ✅ **Legitimate gradient break** - Intentional drop structure (27% gradient)
- ⚠️  **Mixed uphill/downhill** - Multiple uphill sections needing correction

#### Level 3: Complex Scenarios (`test_level3_complex.py`)
- ⚠️  **Multiple gradient breaks** - Long pipeline with various issues
- ⚠️  **Multi-pipeline system** - Connected segments with different issues

#### Level 4: Real-World Scenarios (`test_level4_realworld.py`)
- ⚠️  **Urban terrain challenge** - Complex terrain with multiple constraints

## Test Data Visualization

### ASCII Diagrams
Each scenario includes ASCII profile diagrams showing:
- **Elevation profile** - Pipeline points marked with `*`
- **Gradient chart** - Bar chart showing segment gradients
- **Issue markers** - Visual indicators of problems

#### Legend:
- `*` = Pipeline points
- `<` = Downhill gradient (good)
- `>` = Uphill gradient (problematic)
- `|` = Zero gradient line
- Manhole positions marked with vertical lines

### Example Profile:
```
99.7m **-----------------------------------------------------------------------------| 
      **                            ****                                             |
      **            ****            ****                            ****             |
```

### Example Gradient Chart:
```
Seg 1:  -2.00%                               |<<<<<<<                        OK
Seg 2:  +1.00%                            >>>|                               UPHILL!
Seg 3:  -2.00%                               |<<<<<<<                        OK
```

## TDD Workflow

### Red-Green-Refactor Cycle

1. **RED** 🔴 - Write failing test for next requirement
2. **GREEN** 🟢 - Write minimal code to make test pass
3. **REFACTOR** 🔵 - Improve code quality without breaking tests

### Running Tests

```bash
# Run all basic tests (start here)
pytest tests/sewer_gradient_analysis/test_level1_basic.py -v

# Run specific test
pytest tests/sewer_gradient_analysis/test_level1_basic.py::TestLevel1BasicScenarios::test_perfect_downhill_pipeline_needs_no_correction -v

# Generate test data visualizations
python tests/sewer_gradient_analysis/ascii_visualizer.py
```

### Implementation Order

1. Start with `test_level1_basic.py` - implement basic gradient analysis
2. Move to `test_level2_intermediate.py` - add gradient break detection  
3. Progress to `test_level3_complex.py` - handle multi-segment pipelines
4. Finish with `test_level4_realworld.py` - real-world complexity

## Core Classes to Implement

### `SewerGradientAnalyzer`
Main analysis engine with methods:
- `analyze_scenario()` - Analyze complete sewer system
- `detect_gradient_issues()` - Find problems in pipeline
- `correct_pipeline_gradients()` - Fix gradient issues

### `GradientCorrection` 
Result object containing:
- Original and corrected points
- Correction reasoning
- Before/after gradient metrics

## Key Requirements

### Gradient Standards
- **Minimum gradient**: 0.5% downhill (configurable)
- **Maximum gradient**: No limit (preserve legitimate drops)
- **Flow direction**: Always downhill (negative gradient)

### Constraint Handling
- **Manhole constraints**: Pipeline must connect at invert elevations
- **Gradient break preservation**: Don't smooth out intentional drops
- **Multi-segment logic**: Handle connected pipeline systems

### Issue Detection
- ❌ **Uphill flow** - Any positive gradient
- ❌ **Insufficient gradient** - Below minimum threshold  
- ✅ **Legitimate breaks** - Steep sections in short distances
- ✅ **Normal gradients** - Between 0.5% and reasonable maximum

## Test Scenarios Summary

| Scenario | Complexity | Issues | Expected Corrections |
|----------|------------|--------|---------------------|
| perfect_downhill | Basic | None | 0 |
| simple_uphill_error | Basic | Uphill flow | 1 |
| insufficient_gradient | Basic | Too shallow | 1 |
| legitimate_gradient_break | Intermediate | None (intentional drop) | 0 |
| mixed_uphill_downhill | Intermediate | Multiple uphill sections | 1 |
| multiple_gradient_breaks | Complex | Mixed issues | 1 |
| urban_terrain_challenge | Real-world | Shallow gradients | 1 |

## Getting Started

1. **Examine test data**: Run `python ascii_visualizer.py` to see all scenarios
2. **Start TDD**: Run tests (they will fail initially)
3. **Implement incrementally**: Make one test pass at a time
4. **Visualize results**: Use ASCII diagrams to verify corrections

The test suite provides comprehensive coverage of sewer gradient analysis challenges while maintaining clear visualization of each scenario's requirements and expected outcomes.