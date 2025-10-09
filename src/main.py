from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Line
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
import time
from functools import partial

from dataclasses import dataclass
from typing import List, Tuple

# -----------------------
# Constants & Colors
# -----------------------
CELL_SIZE = dp(44)
CELL_SPACING = dp(4)
FONT_LARGE = dp(22)
FONT_MEDIUM = dp(16)
FONT_SMALL = dp(12)

WHITE = get_color_from_hex("#FFFFFF")
DARK = get_color_from_hex("#2C3E50")
ACCENT = get_color_from_hex("#3498DB")
GOOD = get_color_from_hex("#2ECC71")
BAD = get_color_from_hex("#E74C3C")
PANEL = get_color_from_hex("#ECF0F1")
SUBTLE = get_color_from_hex("#7F8C8D")

# -----------------------
# Data domain model
# -----------------------
@dataclass
class WordSpec:
    word: str
    clue: str
    position: Tuple[int, int] = None  # (row, col) 1-based coordinates
    direction: str = None             # 'across' or 'down'
    number: int = 0

@dataclass
class Puzzle:
    rows: int
    cols: int
    words: List[WordSpec]

# Sample puzzle data - In production, this would come from a service
SAMPLE_PUZZLE = Puzzle(
    rows=16,
    cols=16,
    words=[
        WordSpec(
            word='PYTHON',
            clue='A popular programming language named after néné group',
            position=(2, 3),
            direction='across',
            number=1
        ),
        WordSpec(
            word='PIVY',
            clue='Cross-platform Python framework for GUI development',
            position=(2, 3),
            direction='down',
            number=1
        ),
        WordSpec(
            word='GRYD',
            clue='A structure of intersecting horizontal and vertical lines',
            position=(5, 1),
            direction='across',
            number=2
        ),
        WordSpec(
            word='CODE',
            clue='Instructions written by programmers',
            position=(8, 5),
            direction='down',
            number=2
        ),
        WordSpec(
            word='APP',
            clue='Short for application software',
            position=(7, 8),
            direction='across',
            number=3
        ),
    ]
)

class CrosswordCell(TextInput):
    """Individual cell in the crossword grid"""

    def __init__(self, row, col, **kwargs):
        super().__init__(**kwargs)
        self.row = row
        self.col = col
        self.is_frozen = False
        self.word_ids = []  # Which word(s) this cell belongs to
        self.clue_number = None

        self.multiline = False
        self.write_tab = False
        self.background_normal = ''
        self.background_color = WHITE
        self.foreground_color = DARK
        self.cursor_color = ACCENT
        self.font_size = FONT_LARGE
        self.bold = True
        self.size_hint = (None, None)
        self.size = (CELL_SIZE, CELL_SIZE)
        self.halign = 'center'
        self.padding = [0, CELL_SIZE * 0.2, 0, 0]

        with self.canvas.before:
            Color(*DARK)
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=1.5)

        self.bind(pos=self.update_border, size=self.update_border)
        self.bind(text=self.on_text_change)
        self.bind(focus=self.on_focus_change)

    def update_border(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)

    def on_text_change(self, instance, value):
        if self.is_frozen:
            return
        # Only allow single uppercase letter
        if len(value) > 1:
            self.text = value[-1].upper()
        elif len(value) == 1:
            self.text = value.upper()
        # Navigation is handled by the controller, not here

    def on_focus_change(self, instance, value):
        if value and not self.is_frozen:
            self.background_color = PANEL
        elif not self.is_frozen:
            self.background_color = WHITE

    def freeze(self):
        self.is_frozen = True
        self.readonly = True
        self.background_color = GOOD
        self.foreground_color = WHITE

    def show_incorrect(self):
        """Temporarily show cell as incorrect"""
        if not self.is_frozen:
            self.background_color = BAD
            self.foreground_color = WHITE

    def reset_appearance(self):
        """Reset cell to default appearance"""
        if not self.is_frozen:
            self.background_color = WHITE
            self.foreground_color = DARK

class CrosswordGrid(FloatLayout):
    """Handles only the grid and cell logic, exposes events for the controller"""

    def __init__(self, puzzle_data: Puzzle, **kwargs):
        super().__init__(**kwargs)
        self.puzzle_data = puzzle_data
        self.cells = {}  # (row, col): CrosswordCell
        self.words_completed = set()
        self.on_word_complete = None  # Set by controller

        occupied = set()
        start_positions = {}

        # Find max_row for coordinate transformation
        max_row = 0
        for word_data in puzzle_data.words:
            start_row, start_col = word_data.position
            word = word_data.word
            direction = word_data.direction
            for i in range(len(word)):
                row = start_row if direction == 'across' else start_row + i
                max_row = max(max_row, row)

        for word_data in puzzle_data.words:
            start_row, start_col = word_data.position
            word = word_data.word
            direction = word_data.direction
            number = word_data.number
            if (start_row, start_col) not in start_positions:
                start_positions[(start_row, start_col)] = number
            for i in range(len(word)):
                if direction == 'across':
                    occupied.add((start_row, start_col + i))
                else:
                    occupied.add((start_row + i, start_col))

        self.grid_container = FloatLayout(size_hint=(None, None))

        # Create cells
        for word_idx, word_data in enumerate(puzzle_data.words):
            start_row, start_col = word_data.position
            word = word_data.word
            direction = word_data.direction
            for i in range(len(word)):
                row, col = (start_row, start_col + i) if direction == 'across' else (start_row + i, start_col)
                if (row, col) not in self.cells:
                    cell = CrosswordCell(row, col)
                    cell.pos = (
                        col * (CELL_SIZE + CELL_SPACING),
                        (max_row - row) * (CELL_SIZE + CELL_SPACING)
                    )
                    self.cells[(row, col)] = cell
                    self.grid_container.add_widget(cell)
                    if (row, col) in start_positions:
                        cell.clue_number = start_positions[(row, col)]
                        number_label = Label(
                            text=str(start_positions[(row, col)]),
                            font_size=FONT_SMALL,
                            color=SUBTLE,
                            size_hint=(None, None),
                            size=(FONT_LARGE * 0.7, FONT_LARGE * 0.7),
                            pos=(cell.x + 2, cell.y + cell.height - FONT_LARGE * 0.7)
                        )
                        # Use partial to avoid late binding
                        cell.bind(pos=partial(self._update_number_label_pos, number_label))
                        self.grid_container.add_widget(number_label)
                self.cells[(row, col)].word_ids.append(word_idx)

        max_col = max(pos[1] for pos in occupied)
        max_row = max(pos[0] for pos in occupied)
        grid_width = (max_col + 1) * (CELL_SIZE + CELL_SPACING)
        grid_height = (max_row + 1) * (CELL_SIZE + CELL_SPACING)
        self.grid_container.size = (grid_width, grid_height)

        scroll = ScrollView(do_scroll_x=True, do_scroll_y=True)
        scroll.add_widget(self.grid_container)
        self.add_widget(scroll)

        Clock.schedule_once(self.center_grid, 0.1)

        # Safe binding for word completion check
        for cell in self.cells.values():
            cell.bind(text=partial(self._on_cell_text_change))

    def _update_number_label_pos(self, number_label, cell, pos):
        number_label.pos = (cell.x + 2, cell.y + cell.height - FONT_LARGE * 0.7)

    def _on_cell_text_change(self, *args, **kwargs):
        self.check_word_completion()

    def center_grid(self, dt):
        self.grid_container.pos = (
            (self.width - self.grid_container.width) / 2,
            (self.height - self.grid_container.height) / 2
        )

    def check_word_completion(self):
        for word_idx, word_data in enumerate(self.puzzle_data.words):
            if word_idx in self.words_completed:
                continue
            start_row, start_col = word_data.position
            word = word_data.word
            direction = word_data.direction
            user_word = ''
            cells_in_word = []
            for i in range(len(word)):
                pos = (start_row, start_col + i) if direction == 'across' else (start_row + i, start_col)
                cell = self.cells[pos]
                cells_in_word.append(cell)
                user_word += cell.text
            if user_word == word:
                for cell in cells_in_word:
                    cell.freeze()
                self.words_completed.add(word_idx)
                if self.on_word_complete:
                    self.on_word_complete(word_idx, True)
            elif len(user_word) == len(word) and user_word != word and all(c.text for c in cells_in_word):
                self.show_incorrect_word(cells_in_word)
                if self.on_word_complete:
                    self.on_word_complete(word_idx, False)

    def show_incorrect_word(self, cells):
        for cell in cells:
            cell.show_incorrect()
        def reset_cells(dt):
            for cell in cells:
                if not cell.is_frozen:
                    cell.text = ''
                    cell.reset_appearance()
        Clock.schedule_once(reset_cells, 1.0)

class CluesList(BoxLayout):
    """Display list of clues for across or down"""

    def __init__(self, title, clues, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = CELL_SPACING
        self.padding = CELL_SPACING * 2
        title_label = Label(
            text=f'[b]{title}[/b]',
            markup=True,
            size_hint_y=None,
            height=FONT_LARGE * 1.3,
            font_size=FONT_LARGE,
            color=DARK,
            halign='left',
            valign='middle'
        )
        title_label.bind(size=title_label.setter('text_size'))
        self.add_widget(title_label)
        for number, clue_text in sorted(clues):
            clue_label = Label(
                text=f'[b]{number}.[/b] {clue_text}',
                markup=True,
                size_hint_y=None,
                height=FONT_LARGE * 1.2,
                font_size=FONT_MEDIUM,
                color=SUBTLE,
                halign='left',
                valign='top',
                text_size=(None, None)
            )
            clue_label.bind(width=lambda l, w: l.setter('text_size')(l, (w - CELL_SPACING * 2, None)))
            clue_label.bind(texture_size=lambda l, ts: l.setter('height')(l, ts[1] + CELL_SPACING * 2))
            self.add_widget(clue_label)

class CrosswordApp(App):
    """Main application/controller class"""

    def build(self):
        self.title = 'Crossword Puzzle'
        Window.clearcolor = PANEL
        self.start_time = time.time()
        self.puzzle_data = SAMPLE_PUZZLE

        # Main layout - horizontal split
        main_layout = BoxLayout(orientation='horizontal', spacing=CELL_SPACING * 2, padding=CELL_SPACING * 2)

        # Left side - Grid and header
        left_layout = BoxLayout(orientation='vertical', spacing=CELL_SPACING * 2)

        # Header
        header = BoxLayout(size_hint_y=None, height=FONT_LARGE * 2.5, spacing=CELL_SPACING)
        title_label = Label(
            text='[b]Crossword Puzzle[/b]',
            markup=True,
            font_size=FONT_LARGE,
            color=DARK
        )
        self.timer_label = Label(
            text='Time: 00:00',
            font_size=FONT_MEDIUM,
            color=SUBTLE,
            size_hint_x=0.3
        )
        header.add_widget(title_label)
        header.add_widget(self.timer_label)

        # Crossword grid
        self.grid = CrosswordGrid(self.puzzle_data)
        self.grid.on_word_complete = self.on_word_complete  # Wire event

        left_layout.add_widget(header)
        left_layout.add_widget(self.grid)

        # Right side - Clues
        clues_layout = BoxLayout(orientation='vertical', size_hint_x=0.3, spacing=CELL_SPACING)
        across_clues = []
        down_clues = []
        for word_data in self.puzzle_data.words:
            number = word_data.number
            clue = word_data.clue
            if word_data.direction == 'across':
                across_clues.append((number, clue))
            else:
                down_clues.append((number, clue))
        across_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        across_list = CluesList('ACROSS', across_clues)
        across_scroll.add_widget(across_list)
        down_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        down_list = CluesList('DOWN', down_clues)
        down_scroll.add_widget(down_list)
        clues_layout.add_widget(across_scroll)
        clues_layout.add_widget(down_scroll)

        main_layout.add_widget(left_layout)
        main_layout.add_widget(clues_layout)

        Clock.schedule_interval(self.update_timer, 1)
        Window.bind(on_key_down=self._on_keyboard_down)

        # Wire navigation handlers to cells
        for cell in self.grid.cells.values():
            cell.keyboard_on_key_down = self.make_keyboard_handler(cell)

        return main_layout

    def make_keyboard_handler(self, cell):
        def handler(window, keycode, text, modifiers):
            if cell.is_frozen:
                return
            key, key_str = keycode
            if key_str == 'backspace':
                if cell.text:
                    cell.text = ''
                else:
                    self.move_to_previous_cell(cell)
                return True
            if text and text.isalpha():
                cell.text = text.upper()
                self.move_to_next_cell(cell)
                return True
            if key_str in ['right', 'left', 'up', 'down']:
                self.handle_arrow_key(cell, key_str)
                return True
        return handler

    def _on_keyboard_down(self, window, key, scancode, codepoint, modifier):
        # This helps with keyboard handling on desktop
        pass

    def update_timer(self, dt):
        elapsed = int(time.time() - self.start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        self.timer_label.text = f'Time: {minutes:02d}:{seconds:02d}'

    def move_to_next_cell(self, current_cell):
        if current_cell.is_frozen:
            return
        current_row, current_col = current_cell.row, current_cell.col
        for word_idx in current_cell.word_ids:
            word_data = self.puzzle_data.words[word_idx]
            if word_idx in self.grid.words_completed:
                continue
            start_row, start_col = word_data.position
            direction = word_data.direction
            word_length = len(word_data.word)
            if direction == 'across':
                current_pos_in_word = current_col - start_col
                for offset in range(current_pos_in_word + 1, word_length):
                    next_pos = (current_row, start_col + offset)
                    if next_pos in self.grid.cells and not self.grid.cells[next_pos].is_frozen:
                        self.grid.cells[next_pos].focus = True
                        return
            else:
                current_pos_in_word = current_row - start_row
                for offset in range(current_pos_in_word + 1, word_length):
                    next_pos = (start_row + offset, current_col)
                    if next_pos in self.grid.cells and not self.grid.cells[next_pos].is_frozen:
                        self.grid.cells[next_pos].focus = True
                        return

    def move_to_previous_cell(self, current_cell):
        current_row, current_col = current_cell.row, current_cell.col
        for word_idx in current_cell.word_ids:
            word_data = self.puzzle_data.words[word_idx]
            if word_idx in self.grid.words_completed:
                continue
            start_row, start_col = word_data.position
            direction = word_data.direction
            if direction == 'across':
                current_pos_in_word = current_col - start_col
                if current_pos_in_word > 0:
                    for offset in range(current_pos_in_word - 1, -1, -1):
                        prev_pos = (current_row, start_col + offset)
                        if prev_pos in self.grid.cells and not self.grid.cells[prev_pos].is_frozen:
                            self.grid.cells[prev_pos].focus = True
                            self.grid.cells[prev_pos].text = ''
                            return
            else:
                current_pos_in_word = current_row - start_row
                if current_pos_in_word > 0:
                    for offset in range(current_pos_in_word - 1, -1, -1):
                        prev_pos = (start_row + offset, current_col)
                        if prev_pos in self.grid.cells and not self.grid.cells[prev_pos].is_frozen:
                            self.grid.cells[prev_pos].focus = True
                            self.grid.cells[prev_pos].text = ''
                            return

    def handle_arrow_key(self, current_cell, direction):
        current_row, current_col = current_cell.row, current_cell.col
        if direction == 'right':
            next_pos = (current_row, current_col + 1)
        elif direction == 'left':
            next_pos = (current_row, current_col - 1)
        elif direction == 'down':
            next_pos = (current_row + 1, current_col)
        elif direction == 'up':
            next_pos = (current_row - 1, current_col)
        else:
            return
        if next_pos in self.grid.cells:
            self.grid.cells[next_pos].focus = True

    def on_word_complete(self, word_idx, is_correct):
        if is_correct:
            if len(self.grid.words_completed) == len(self.puzzle_data.words):
                self.show_congratulations()

    def show_congratulations(self):
        elapsed = int(time.time() - self.start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        content = BoxLayout(orientation='vertical', padding=CELL_SPACING * 5, spacing=CELL_SPACING * 3)
        congrats_label = Label(
            text='[b]Congratulations![/b]',
            markup=True,
            font_size=FONT_LARGE * 1.3,
            color=GOOD,
            size_hint_y=None,
            height=FONT_LARGE * 2
        )
        time_label = Label(
            text=f'You completed the puzzle in\n{minutes:02d}:{seconds:02d}',
            font_size=FONT_MEDIUM,
            halign='center',
            color=DARK
        )
        close_btn = Button(
            text='Close',
            size_hint_y=None,
            height=FONT_LARGE * 2,
            background_normal='',
            background_color=ACCENT,
            color=WHITE
        )
        content.add_widget(congrats_label)
        content.add_widget(time_label)
        content.add_widget(close_btn)
        popup = Popup(
            title='',
            content=content,
            size_hint=(0.8, 0.5),
            separator_height=0
        )
        close_btn.bind(on_press=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    CrosswordApp().run()
