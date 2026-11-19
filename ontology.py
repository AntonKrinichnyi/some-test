import turtle
from dataclasses import dataclass


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Segment:
    start: Point
    end: Point


@dataclass
class VisualStyling:
    color: str = "blue"
    thickness: float = 1.5
    line_type: str = "solid"  # "solid" або "dashed"


class Fractal:
    def __init__(self, iteration_depth: int, style: VisualStyling):
        self.iteration_depth = iteration_depth
        self.style = style
        self.segments: list[Segment] = []

    def generate(self) -> list[Segment]:
        raise NotImplementedError("Метод generate має бути перевизначений у підкласі")


class SierpinskiTriangleFractal(Fractal):
    def __init__(
        self,
        iteration_depth: int,
        style: VisualStyling,
        p1: Point = Point(-200, -150),
        p2: Point = Point(200, -150),
        p3: Point = Point(0, 196.4),
    ):
        super().__init__(iteration_depth, style)
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self._triangles: list[tuple[Point, Point, Point]] = [
            (self.p1, self.p2, self.p3)
        ]

    @staticmethod
    def _midpoint(a: Point, b: Point) -> Point:
        return Point((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)

    def generate(self) -> list[Segment]:
        """
        Генерує трикутники на заданій глибині та перетворює їх на список відрізків.
        """
        triangles: list[tuple[Point, Point, Point]] = [(self.p1, self.p2, self.p3)]

        for _ in range(max(0, self.iteration_depth)):
            next_triangles: list[tuple[Point, Point, Point]] = []
            for a, b, c in triangles:
                m_ab = self._midpoint(a, b)
                m_bc = self._midpoint(b, c)
                m_ca = self._midpoint(c, a)

                # Три кутові трикутники
                next_triangles.append((a, m_ab, m_ca))
                next_triangles.append((m_ab, b, m_bc))
                next_triangles.append((m_ca, m_bc, c))
            triangles = next_triangles

        self._triangles = triangles
        segments: list[Segment] = []
        for a, b, c in self._triangles:
            segments.extend(
                [
                    Segment(a, b),
                    Segment(b, c),
                    Segment(c, a),
                ]
            )

        self.segments = segments
        return self.segments

    def draw(self):
        """Малює трикутник Серпінського з урахуванням VisualStyling."""
        if not self.segments:
            self.generate()

        screen = turtle.Screen()
        screen.title(f"Трикутник Серпінського (ітерацій: {self.iteration_depth})")
        screen.setup(width=900, height=700)

        pen = turtle.Turtle()
        pen.speed(0)
        pen.hideturtle()
        pen.color(self.style.color)
        pen.pensize(self.style.thickness)

        screen.tracer(0, 0)

        for seg in self.segments:
            pen.penup()
            pen.goto(seg.start.x, seg.start.y)
            pen.pendown()

            if self.style.line_type == "dashed":
                mid_x = (seg.start.x + seg.end.x) / 2.0
                mid_y = (seg.start.y + seg.end.y) / 2.0
                pen.goto(mid_x, mid_y)
                pen.penup()
                pen.goto(seg.end.x, seg.end.y)
            else:
                pen.goto(seg.end.x, seg.end.y)

        screen.update()
        screen.exitonclick()


if __name__ == "__main__":
    style = VisualStyling(color="orange", thickness=2.0, line_type="solid")
    sierpinski = SierpinskiTriangleFractal(iteration_depth=5, style=style)
    sierpinski.generate()
    sierpinski.draw()
