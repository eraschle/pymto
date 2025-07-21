"""
ASCII Visualizer for Sewer Gradient Analysis

Creates simple ASCII diagrams to visualize pipeline profiles
when matplotlib is not available.
"""

from test_data_generator import SewerPipeline, SewerScenario


class ASCIISewerVisualizer:
    """Creates ASCII visualizations of sewer pipeline profiles."""

    @staticmethod
    def create_profile_diagram(scenario: SewerScenario, width: int = 80, height: int = 15) -> str:
        """
        Create ASCII profile diagram of sewer scenario.

        Args:
            scenario: SewerScenario to visualize
            width: Character width of diagram
            height: Character height of diagram

        Returns:
            String containing ASCII diagram
        """
        lines = []
        lines.append("=" * width)
        lines.append(f"SCENARIO: {scenario.name} ({scenario.complexity.value})")
        lines.append(f"DESC: {scenario.description}")
        lines.append("=" * width)

        # Get all points from all pipelines
        all_points = []
        pipeline_labels = []

        for pipeline in scenario.pipelines:
            for i, point in enumerate(pipeline.points):
                cumulative_distance = 0
                for j in range(i):
                    cumulative_distance += pipeline.points[j].distance_2d(pipeline.points[j + 1])
                all_points.append((cumulative_distance, point.z, pipeline.id))
                pipeline_labels.append(f"{pipeline.id}[{i}]")

        if not all_points:
            return "No pipeline data to visualize"

        # Calculate bounds
        distances = [p[0] for p in all_points]
        elevations = [p[1] for p in all_points]
        min_dist, max_dist = min(distances), max(distances)
        min_elev, max_elev = min(elevations), max(elevations)

        # Add some padding
        elev_range = max_elev - min_elev
        min_elev -= elev_range * 0.1
        max_elev += elev_range * 0.1

        # Create the profile
        profile_lines = []

        # Create coordinate system
        for row in range(height):
            line_chars = []
            current_elevation = max_elev - (row / (height - 1)) * (max_elev - min_elev)

            for col in range(width):
                current_distance = min_dist + (col / (width - 1)) * (max_dist - min_dist)

                # Check if there's a point near this position
                char = " "

                # Look for pipeline points
                for i, (dist, elev, pipe_id) in enumerate(all_points):
                    dist_tolerance = (max_dist - min_dist) / width * 2
                    elev_tolerance = (max_elev - min_elev) / height * 2

                    if (
                        abs(dist - current_distance) <= dist_tolerance
                        and abs(elev - current_elevation) <= elev_tolerance
                    ):
                        char = "*"
                        break

                # Add grid lines
                if col == 0 or col == width - 1:
                    char = "|" if char == " " else char
                if row == 0 or row == height - 1:
                    char = "-" if char == " " else char

                line_chars.append(char)

            # Add elevation labels
            elev_label = f"{current_elevation:.1f}m"
            line_str = "".join(line_chars)
            if row % 3 == 0:  # Add labels every 3rd row
                line_str = f"{elev_label:>6} {line_str}"
            else:
                line_str = f"       {line_str}"

            profile_lines.append(line_str)

        # Add distance labels
        dist_labels = "       "
        for i in range(0, width, 10):
            current_distance = min_dist + (i / (width - 1)) * (max_dist - min_dist)
            dist_labels += f"{current_distance:>8.0f}m"

        profile_lines.append(dist_labels)

        lines.extend(profile_lines)

        # Add manhole information
        lines.append("")
        lines.append("MANHOLES:")
        for manhole in scenario.manholes:
            lines.append(
                f"  {manhole.id}: Cover={manhole.cover_elevation:.1f}m, Invert={manhole.invert_elevation:.1f}m"
            )

        # Add pipeline information
        lines.append("")
        lines.append("PIPELINES:")
        for pipeline in scenario.pipelines:
            gradients = pipeline.get_gradients()
            avg_gradient = sum(gradients) / len(gradients) if gradients else 0
            lines.append(f"  {pipeline.id}: {len(pipeline.points)} points, Avg gradient: {avg_gradient:.2f}%")

            if pipeline.expected_issues:
                lines.append(f"    Expected issues: {', '.join(pipeline.expected_issues)}")

        return "\n".join(lines)

    @staticmethod
    def create_gradient_chart(pipeline: SewerPipeline, width: int = 60) -> str:
        """Create ASCII bar chart of gradients."""
        gradients = pipeline.get_gradients()

        if not gradients:
            return "No gradients to display"

        lines = []
        lines.append(f"GRADIENT CHART - {pipeline.id}")
        lines.append("=" * width)

        # Find range
        min_grad, max_grad = min(gradients), max(gradients)
        abs_max = max(abs(min_grad), abs(max_grad))

        if abs_max == 0:
            abs_max = 1  # Avoid division by zero

        # Create chart
        for i, gradient in enumerate(gradients):
            # Normalize gradient to chart width
            bar_length = int(abs(gradient) / abs_max * (width // 2))

            if gradient >= 0:
                # Uphill (positive) - show as problem
                bar = " " * (width // 2 - bar_length) + ">" * bar_length + "|" + " " * (width // 2)
                marker = "UPHILL!"
            else:
                # Downhill (negative) - normal
                bar = " " * (width // 2) + "|" + "<" * bar_length + " " * (width // 2 - bar_length)
                marker = "OK" if abs(gradient) >= 0.5 else "SHALLOW"

            lines.append(f"Seg{i + 1:2}: {gradient:+6.2f}% {bar} {marker}")

        # Add reference lines
        lines.append("")
        lines.append("Legend: < = Downhill (good), > = Uphill (bad), | = Zero gradient")
        lines.append("Minimum recommended gradient: -0.5% (downhill)")

        return "\n".join(lines)


def create_all_visualizations():
    """Create ASCII visualizations for all test scenarios."""
    from test_data_generator import generate_all_test_scenarios

    scenarios = generate_all_test_scenarios()

    print("SEWER GRADIENT ANALYSIS - TEST SCENARIOS")
    print("=" * 80)
    print(f"Generated {len(scenarios)} test scenarios for TDD development")
    print("=" * 80)

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n\n[{i}/{len(scenarios)}] " + "=" * 50)
        print(ASCIISewerVisualizer.create_profile_diagram(scenario))

        # Add gradient charts for each pipeline
        for pipeline in scenario.pipelines:
            print("\n" + "-" * 40)
            print(ASCIISewerVisualizer.create_gradient_chart(pipeline))

        print("=" * 80)

        # Add interpretation
        print("INTERPRETATION:")
        if scenario.expected_corrections == 0:
            print("  ✓ This scenario should require NO corrections")
        else:
            print(f"  ⚠ This scenario should require {scenario.expected_corrections} correction(s)")

        for pipeline in scenario.pipelines:
            if pipeline.expected_issues:
                print(f"  ⚠ {pipeline.id} has issues: {', '.join(pipeline.expected_issues)}")
            else:
                print(f"  ✓ {pipeline.id} should be problem-free")


if __name__ == "__main__":
    create_all_visualizations()
