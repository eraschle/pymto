import re
from dataclasses import dataclass

from ...models import ObjectData, ObjectType, ShapeType
from ...protocols import IDimensionCalculator


@dataclass
class ConduitPipe:
    material: str
    diameter: float


class ConduitBankCalculator(IDimensionCalculator):
    pattern = re.compile(r"(?P<count>\d+)\s*[xX*]\s*(?P<material>\D*)\s*(?P<dim>\d+)")

    def __init__(self, cap_between_pipes: float, max_pipes_per_row: int) -> None:
        self.cap_between_pipes = cap_between_pipes
        self.max_pipes_per_row = max_pipes_per_row

    def calculate_dimension(self, elements: list[ObjectData]) -> None:
        """Calculate dimensions for conduit bank objects.

        Parameters
        ----------
        objects : list[ObjectData]
            List of ObjectData representing conduit bank elements
        """
        for element in elements:
            if element.object_type != ObjectType.CONDUIT_BANK:
                continue
            self._calculate_dimensions(element)

    def _calculate_dimensions(self, element: ObjectData) -> None:
        """Calculate specific dimensions for a conduit bank object."""
        if element.assigned_text is None:
            return
        assigned_text = element.assigned_text.content
        matches = self.pattern.findall(assigned_text)
        if len(matches) == 0:
            return
        pipes = self._create_pipes(matches)
        pipe_rows = self._create_pipe_rows(pipes)
        width = self._calculate_bank_width(pipe_rows=pipe_rows)
        element.dimension.set_shape_type(ShapeType.RECTANGULAR)
        element.dimension.reset_round_dimension()
        element.dimension.width = width / 1000
        depth = self._calculate_bank_depth(pipe_rows=pipe_rows)
        element.dimension.depth = depth / 1000

    def _create_pipes(self, matches: list[re.Match]) -> list[ConduitPipe]:
        pipes = []
        for pipe_match in matches:
            count = int(pipe_match[0])
            material = pipe_match[1].strip()
            dimension = float(pipe_match[2])
            pipes.extend([ConduitPipe(material, dimension) for _ in range(count)])
        return sorted(pipes, key=lambda pipe: pipe.diameter, reverse=True)

    def _create_pipe_rows(self, pipes: list[ConduitPipe]) -> list[list[ConduitPipe]]:
        pipe_rows = []
        while len(pipes) > 0:
            row = pipes[: self.max_pipes_per_row]
            pipe_rows.append(row)
            pipes = pipes[self.max_pipes_per_row :]
        return pipe_rows

    def _calculate_bank_width(self, pipe_rows: list[list[ConduitPipe]]) -> float:
        row_widths = [self._calculate_row_width(row) for row in pipe_rows]
        return max(row_widths)

    def _calculate_row_width(self, pipes: list[ConduitPipe]) -> float:
        sum_diameter = sum([pipe.diameter for pipe in pipes])
        width_caps = (len(pipes) + 1) * self.cap_between_pipes
        return sum_diameter + width_caps

    def _calculate_bank_depth(self, pipe_rows: list[list[ConduitPipe]]) -> float:
        row_height = sum([self._calculate_row_depth(row) for row in pipe_rows])
        height_caps = (len(pipe_rows) + 1) * self.cap_between_pipes
        return row_height + height_caps

    def _calculate_row_depth(self, pipes: list[ConduitPipe]) -> float:
        max_diameter = max([pipe.diameter for pipe in pipes])
        return max_diameter
