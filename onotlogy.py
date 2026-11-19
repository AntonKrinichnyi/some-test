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
    color: str = "red"
    thickness: float = 1.5
    line_type: str = "solid"  # "solid" или "dashed"


class Fractal:
    def __init__(self, iteration_depth: int, style: VisualStyling):
        self.iteration_depth = iteration_depth
        self.style = style
        self.segments: list[Segment] = []

    def generate(self):
        raise NotImplementedError(
            "Метод generate должен быть переопределён в подклассе"
        )


class DragonFractal(Fractal):
    def __init__(
        self,
        iteration_depth: int,
        style: VisualStyling,
        start_point: Point = Point(-150, 0),
        end_point: Point = Point(150, 0),
        turn_angle: float = 90.0,
    ):
        super().__init__(iteration_depth, style)
        self.start_point = start_point
        self.end_point = end_point
        self.turn_angle = turn_angle
        self.segments = [Segment(self.start_point, self.end_point)]

    @staticmethod
    def _build_turns(depth: int) -> list[int]:
        """
        Генерирует последовательность поворотов для кривой Дракона:
        1 — поворот влево, -1 — поворот вправо.
        """
        turns: list[int] = []
        for _ in range(depth):
            # Копируем текущую последовательность, инвертируем знаки и добавляем поворот влево (1)
            reversed_inverted = [-t for t in reversed(turns)]
            turns = turns + [1] + reversed_inverted
        return turns

    def generate(self) -> list[Segment]:
        """
        Порождает набор отрезков на заданной глубине итерации.
        Начальное условие: один отрезок от start_point до end_point.
        Условие завершения: выполнено iteration_depth шагов.
        """
        if self.iteration_depth <= 0:
            self.segments = [Segment(self.start_point, self.end_point)]
            return self.segments

        turns = self._build_turns(self.iteration_depth)

        # Длина каждого сегмента на глубине n: L / (sqrt(2) ** n)
        base_dx = self.end_point.x - self.start_point.x
        base_dy = self.end_point.y - self.start_point.y
        scale = 1.0 / ((2.0**0.5) ** self.iteration_depth)

        # Первый шаг: наклон на +45 градусов (или -45 в зависимости от направления)
        # Для классического дракона первый поворот на +45°
        import math

        rad_45 = math.radians(45 * (self.turn_angle / 90.0))
        cos_a = math.cos(rad_45)
        sin_a = math.sin(rad_45)

        dx = (base_dx * cos_a - base_dy * sin_a) * scale
        dy = (base_dx * sin_a + base_dy * cos_a) * scale

        current = Point(self.start_point.x, self.start_point.y)
        new_segments: list[Segment] = []

        # Направление текущего вектора: 0 -> вправо, 1 -> вверх, 2 -> влево, 3 -> вниз
        # Упрощённо вращаем вектор (dx, dy) на ±90° согласно списку turns
        # При повороте влево на 90°: (x, y) -> (-y, x)
        # При повороте вправо на 90°: (x, y) -> (y, -x)
        # Первый отрезок идёт под +45°, а turns[i] задаёт изменение направления на каждом шаге
        cur_dx, cur_dy = dx, dy
        next_pt = Point(current.x + cur_dx, current.y + cur_dy)
        new_segments.append(Segment(current, next_pt))
        current = next_pt

        for turn in turns:
            if turn == 1:  # влево на 90°
                cur_dx, cur_dy = -cur_dy, cur_dx
            else:  # вправо на 90°
                cur_dx, cur_dy = cur_dy, -cur_dx

            next_pt = Point(current.x + cur_dx, current.y + cur_dy)
            new_segments.append(Segment(current, next_pt))
            current = next_pt

        self.segments = new_segments
        return self.segments

    def draw(self):
        """Отрисовка фрактала с учётом параметров VisualStyling."""
        if not self.segments:
            self.generate()

        screen = turtle.Screen()
        screen.title(f"Кривая Дракона (итераций: {self.iteration_depth})")
        screen.setup(width=900, height=700)

        pen = turtle.Turtle()
        pen.speed(0)
        pen.hideturtle()
        pen.color(self.style.color)
        pen.pensize(self.style.thickness)

        # Отключаем анимацию для мгновенной отрисовки на больших глубинах
        screen.tracer(0, 0)

        for seg in self.segments:
            pen.penup()
            pen.goto(seg.start.x, seg.start.y)
            pen.pendown()

            if self.style.line_type == "dashed":
                # Простая штриховка для каждого сегмента
                mid_x = (seg.start.x + seg.end.x) / 2
                mid_y = (seg.start.y + seg.end.y) / 2
                pen.goto(mid_x, mid_y)
                pen.penup()
                pen.goto(seg.end.x, seg.end.y)
            else:
                pen.goto(seg.end.x, seg.end.y)

        screen.update()
        screen.exitonclick()


if __name__ == "__main__":
    # Пример 1: индивід Dragon_Iteration5
    # style_1 = VisualStyling(color="red", thickness=1.5, line_type="solid")
    # dragon_5 = DragonFractal(iteration_depth=5, style=style_1)
    # dragon_5.generate()
    # dragon_5.draw()

    # Пример 2: индивід Dragon_Iteration10 (раскомментируйте для проверки)
    style_2 = VisualStyling(color="green", thickness=2.0, line_type="solid")
    dragon_10 = DragonFractal(iteration_depth=10, style=style_2)
    dragon_10.generate()
    dragon_10.draw()
