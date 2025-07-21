#!/usr/bin/env python3
"""
Quick scenario viewer - show individual scenarios easily.

Usage:
    python show_scenario.py                    # Interactive selection
    python show_scenario.py perfect_downhill   # Show specific scenario  
    python show_scenario.py --list            # List all scenarios
    python show_scenario.py uphill            # Show scenarios matching 'uphill'
"""

import sys
from test_data_generator import generate_all_test_scenarios
from ascii_visualizer import ASCIISewerVisualizer


def list_scenarios():
    """List all available scenarios."""
    scenarios = generate_all_test_scenarios()
    
    print("Available test scenarios:")
    print("=" * 50)
    for i, scenario in enumerate(scenarios, 1):
        status = "✅ NO issues" if scenario.expected_corrections == 0 else f"⚠️  {scenario.expected_corrections} correction(s)"
        print(f"{i:2}. {scenario.name:<25} ({scenario.complexity.value:<12}) - {status}")
    print("=" * 50)
    return scenarios


def show_scenario_by_name(name: str):
    """Show specific scenario by name or partial match."""
    scenarios = generate_all_test_scenarios()
    
    # Find exact match first
    matching = [s for s in scenarios if s.name == name]
    
    # If no exact match, try partial match
    if not matching:
        matching = [s for s in scenarios if name.lower() in s.name.lower()]
    
    if not matching:
        print(f"❌ No scenario found matching '{name}'")
        print("\nAvailable scenarios:")
        for scenario in scenarios:
            print(f"  - {scenario.name}")
        return
    
    if len(matching) > 1:
        print(f"Multiple scenarios match '{name}':")
        for i, scenario in enumerate(matching, 1):
            print(f"{i}. {scenario.name}")
        
        # If not interactive (no stdin), show first match
        if not sys.stdin.isatty():
            print(f"\nShowing first match: {matching[0].name}")
            show_single_scenario(matching[0])
            return
            
        try:
            choice = int(input("\nSelect scenario (number): ")) - 1
            if 0 <= choice < len(matching):
                show_single_scenario(matching[choice])
            else:
                print("Invalid selection")
        except (ValueError, KeyboardInterrupt, EOFError):
            print("Cancelled")
        return
    
    show_single_scenario(matching[0])


def show_single_scenario(scenario):
    """Show a single scenario with full details."""
    print("🔍 SINGLE SCENARIO VIEW")
    print("=" * 80)
    print(ASCIISewerVisualizer.create_profile_diagram(scenario))
    
    # Show gradient charts
    for pipeline in scenario.pipelines:
        print("\n" + "-" * 60)
        print(ASCIISewerVisualizer.create_gradient_chart(pipeline))
    
    print("\n" + "=" * 80)
    print("📋 SUMMARY:")
    if scenario.expected_corrections == 0:
        print("  ✅ This scenario should require NO corrections")
    else:
        print(f"  ⚠️  This scenario should require {scenario.expected_corrections} correction(s)")
    
    for pipeline in scenario.pipelines:
        if pipeline.expected_issues:
            print(f"  🔧 {pipeline.id} has issues: {', '.join(pipeline.expected_issues)}")
        else:
            print(f"  ✅ {pipeline.id} should be problem-free")


def interactive_selection():
    """Interactive scenario selection."""
    scenarios = list_scenarios()
    
    print(f"\nEnter scenario number (1-{len(scenarios)}) or name:")
    try:
        user_input = input("> ").strip()
        
        if user_input.isdigit():
            # Numeric selection
            choice = int(user_input) - 1
            if 0 <= choice < len(scenarios):
                show_single_scenario(scenarios[choice])
            else:
                print("❌ Invalid number")
        else:
            # Name-based selection
            show_scenario_by_name(user_input)
            
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled")


def main():
    """Main entry point."""
    if len(sys.argv) == 1:
        # No arguments - interactive mode
        interactive_selection()
    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        if arg in ['-l', '--list']:
            list_scenarios()
        elif arg in ['-h', '--help']:
            print(__doc__)
        else:
            # Show specific scenario
            show_scenario_by_name(arg)
    else:
        print("Usage: python show_scenario.py [scenario_name|--list|--help]")


if __name__ == "__main__":
    main()