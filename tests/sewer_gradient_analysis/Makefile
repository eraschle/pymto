# Makefile for Sewer Gradient Analysis TDD Suite

.PHONY: help visualize show list test-basic test-all test-level1 test-level2 test-level3 test-level4 test-tdd clean

# Default target
help:
	@echo "Sewer Gradient Analysis TDD Suite"
	@echo "================================="
	@echo ""
	@echo "Available targets:"
	@echo "  help         Show this help message"
	@echo "  visualize    Generate ASCII visualizations of ALL test scenarios"
	@echo "  show         Show single scenario interactively"
	@echo "  list         List all available scenarios"
	@echo "  test-basic   Run only basic (Level 1) tests"
	@echo "  test-level1  Run Level 1 tests (alias for test-basic)"
	@echo "  test-level2  Run Level 2 intermediate tests"
	@echo "  test-level3  Run Level 3 complex tests"  
	@echo "  test-level4  Run Level 4 real-world tests"
	@echo "  test-all     Run all tests"
	@echo "  test-tdd     Run tests with TDD markers"
	@echo "  data         Generate test data summary"
	@echo "  clean        Clean up temporary files"
	@echo ""
	@echo "Quick Commands:"
	@echo "  make show            # Interactive scenario selection"
	@echo "  make list            # List all scenarios" 
	@echo ""
	@echo "TDD Workflow:"
	@echo "  1. make list         # See available scenarios"
	@echo "  2. make show         # Examine specific scenarios"
	@echo "  3. make test-level1  # Start with basic tests (will fail)"
	@echo "  4. Implement code to make tests pass"
	@echo "  5. make test-level2  # Move to intermediate tests"
	@echo "  6. Continue with level3, level4..."

# Generate visualizations
visualize:
	@echo "Generating ASCII visualizations..."
	@python ascii_visualizer.py

# Show single scenario interactively
show:
	@echo "Interactive scenario selection:"
	@python show_scenario.py

# List all scenarios
list:
	@echo "Available test scenarios:"
	@python show_scenario.py --list

# Generate test data summary  
data:
	@echo "Generating test data summary..."
	@python test_data_generator.py

# Test targets
test-basic test-level1:
	@echo "Running Level 1 (Basic) tests..."
	@pytest test_level1_basic.py -v --tb=short

test-level2:
	@echo "Running Level 2 (Intermediate) tests..."
	@pytest -m intermediate -v --tb=short || echo "Level 2 tests not implemented yet"

test-level3:
	@echo "Running Level 3 (Complex) tests..."
	@pytest -m complex -v --tb=short || echo "Level 3 tests not implemented yet" 

test-level4:
	@echo "Running Level 4 (Real-world) tests..."
	@pytest -m real_world -v --tb=short || echo "Level 4 tests not implemented yet"

test-all:
	@echo "Running all tests..."
	@pytest . -v --tb=short

test-tdd:
	@echo "Running TDD tests..."
	@pytest -m tdd -v --tb=short

# Clean up
clean:
	@echo "Cleaning up..."
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache

# Quick start for new developers
quickstart: data visualize
	@echo ""
	@echo "🚀 Quick Start Complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Review the visualizations above to understand test scenarios"
	@echo "2. Run 'make test-basic' to see failing tests (this is expected!)"
	@echo "3. Implement SewerGradientAnalyzer class to make tests pass"
	@echo "4. Use Red-Green-Refactor TDD cycle"
	@echo ""
	@echo "See README.md for detailed instructions."