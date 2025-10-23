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
from functools import partial

from domain import (
    PuzzleSpec,
    WordSpec,
    generate_crossword_puzzle,
    mock_generate_words_clues,
)
from store import PuzzleStore

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

    def __init__(self, puzzle: PuzzleSpec, **kwargs):
        super().__init__(**kwargs)
        self.puzzle = puzzle
        self.cells = {}
        self.words_completed = set()
        self.on_word_complete = None

        if not puzzle or not puzzle.words:
            return

        occupied = set()
        start_positions = {}

        max_row = max((ws.position[0] for ws in puzzle.words), default=1)
        max_col = max((ws.position[1] for ws in puzzle.words), default=1)

        for ws in puzzle.words:
            start_positions[(ws.position[0], ws.position[1])] = ws.number
            word = ws.word
            direction = ws.direction
            row, col = ws.position
            for i in range(len(word)):
                if direction == 'across':
                    occupied.add((row, col + i))
                else:
                    occupied.add((row + i, col))

        self.grid_container = FloatLayout(size_hint=(None, None))

        for word_idx, ws in enumerate(puzzle.words):
            word = ws.word
            direction = ws.direction
            row, col = ws.position
            for i in range(len(word)):
                r, c = (row, col + i) if direction == 'across' else (row + i, col)
                if (r, c) not in self.cells:
                    cell = CrosswordCell(r, c)
                    cell.pos = (
                        (c - 1) * (CELL_SIZE + CELL_SPACING),
                        (max_row - r) * (CELL_SIZE + CELL_SPACING)
                    )
                    self.cells[(r, c)] = cell
                    self.grid_container.add_widget(cell)
                    if (r, c) in start_positions:
                        cell.clue_number = start_positions[(r, c)]
                        number_label = Label(
                            text=str(start_positions[(r, c)]),
                            font_size=FONT_SMALL,
                            color=SUBTLE,
                            size_hint=(None, None),
                            size=(FONT_LARGE * 0.7, FONT_LARGE * 0.7),
                            pos=(cell.x + 2, cell.y + cell.height - FONT_LARGE * 0.7)
                        )
                        # Use partial to avoid late binding
                        cell.bind(pos=partial(self._update_number_label_pos, number_label))
                        self.grid_container.add_widget(number_label)
                self.cells[(r, c)].word_ids.append(word_idx)

        grid_width = (max_col) * (CELL_SIZE + CELL_SPACING)
        grid_height = (max_row) * (CELL_SIZE + CELL_SPACING)
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
        for word_idx, ws in enumerate(self.puzzle.words):
            if word_idx in self.words_completed:
                continue
            row, col = ws.position
            word = ws.word
            direction = ws.direction
            user_word = ''
            cells_in_word = []
            for i in range(len(word)):
                pos = (row, col + i) if direction == 'across' else (row + i, col)
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
        self.start_time = None
        self.timer_running = True
        self.puzzle_store = PuzzleStore()
        self.current_puzzle = None
        self.current_grid = None
        self.current_no = None

        # Main layout - horizontal split
        self.main_layout = BoxLayout(orientation='horizontal', spacing=CELL_SPACING * 2, padding=CELL_SPACING * 2)

        # Left side - Grid and header
        self.left_layout = BoxLayout(orientation='vertical', spacing=CELL_SPACING * 2)

        # Header/Menu bar
        self.header = BoxLayout(size_hint_y=None, height=FONT_LARGE * 2.5, spacing=CELL_SPACING)

        # "New" button
        self.new_btn = Button(
            text='New',
            size_hint_x=None,
            width=dp(70),
            background_color=ACCENT,
            color=WHITE,
            font_size=FONT_MEDIUM
        )
        self.new_btn.bind(on_press=self.on_new_puzzle)

        # "Delete" button
        self.delete_btn = Button(
            text='Delete',
            size_hint_x=None,
            width=dp(70),
            background_color=BAD,
            color=WHITE,
            font_size=FONT_MEDIUM,
            disabled=True  # Initially disabled
        )
        self.delete_btn.bind(on_press=self.on_delete_puzzle)

        # Title label (will be updated)
        self.title_label = Label(
            text='Press New to create your first Puzzle',
            markup=True,
            font_size=FONT_LARGE,
            color=DARK,
            size_hint_x=1
        )

        # Pause button
        self.pause_btn = Button(
            text='Pause',
            size_hint_x=None,
            width=dp(70),
            background_color=SUBTLE,
            color=WHITE,
            font_size=FONT_MEDIUM,
            disabled=True  # Initially disabled
        )
        self.pause_btn.bind(on_press=self.on_pause_timer)

        # Timer label
        self.timer_label = Label(
            text='Time: 00:00',
            font_size=FONT_MEDIUM,
            color=SUBTLE,
            size_hint_x=None,
            width=dp(100)
        )

        self.header.add_widget(self.new_btn)
        self.header.add_widget(self.delete_btn)
        self.header.add_widget(self.title_label)
        self.header.add_widget(self.pause_btn)
        self.header.add_widget(self.timer_label)

        self.left_layout.add_widget(self.header)

        # Placeholder for grid (will be replaced)
        self.grid_container = BoxLayout()
        self.left_layout.add_widget(self.grid_container)

        # Right side - Clues
        self.clues_layout = BoxLayout(orientation='vertical', size_hint_x=0.3, spacing=CELL_SPACING)
        self.across_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.down_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.clues_layout.add_widget(self.across_scroll)
        self.clues_layout.add_widget(self.down_scroll)

        self.main_layout.add_widget(self.left_layout)
        self.main_layout.add_widget(self.clues_layout)

        # Check if store is empty
        if not self.puzzle_store.list_puzzles():
            self.display_empty_state()
        else:
            self.load_latest_puzzle()

        Clock.schedule_interval(self.update_timer, 1)
        Window.bind(on_key_down=self._on_keyboard_down)

        return self.main_layout

    def display_empty_state(self):
        self.grid_container.clear_widgets()
        self.across_scroll.clear_widgets()
        self.down_scroll.clear_widgets()
        self.title_label.text = 'Press New to create your first Puzzle'
        self.delete_btn.disabled = True
        self.pause_btn.disabled = True
        self.timer_label.text = 'Time: 00:00'

    def update_header(self):
        # Update title with puzzle number
        if self.current_no is not None:
            self.title_label.text = f'[b]Crossword Puzzle no.{self.current_no}[/b]'
        else:
            self.title_label.text = '[b]Crossword Puzzle[/b]'

    def load_latest_puzzle(self):
        puzzles = self.puzzle_store.list_puzzles()
        if not puzzles:
            self.display_empty_state()
            return
        no, pid = puzzles[-1]
        data = self.puzzle_store.store.get(pid)
        puzzle = PuzzleSpec.from_dict(data)
        self.current_puzzle = puzzle
        self.current_no = no
        self.display_puzzle(puzzle)

    def load_new_puzzle(self, *args):
        # Show feedback popup
        popup = Popup(
            title='Generating Puzzle',
            content=Label(text='Generating words and clues...'),
            size_hint=(0.5, 0.3),
            auto_dismiss=False
        )
        popup.open()
        # Step 1: Generate new words/clues
        # word_clues = mock_generate_words_clues(8)
        word_clues = [{"word": w, "clue": f"Clue for {w}"} for w in ["PYTHON", "TONUS", "OUR", "MOTOR", "NEOCITRON"]]
        popup.content.text = 'Generating crossword grid...'
        # Step 2: Generate crossword puzzle
        puzzle, excluded = generate_crossword_puzzle([(wc['word'], wc['clue']) for wc in word_clues])
        # Step 3: Save puzzle to store
        self.puzzle_store.save_puzzle(puzzle)
        # Step 4: Set as current
        puzzles = self.puzzle_store.list_puzzles()
        for no, pid in puzzles:
            if pid == puzzle.id:
                self.current_no = no
                break
        else:
            self.current_no = None
        self.current_puzzle = puzzle
        # Step 5: Update UI
        self.display_puzzle(puzzle)
        popup.dismiss()

    def display_puzzle(self, puzzle: PuzzleSpec):
        self.grid_container.clear_widgets()
        self.current_grid = CrosswordGrid(puzzle)
        self.current_grid.on_word_complete = self.on_word_complete
        self.grid_container.add_widget(self.current_grid)
        # Update clues
        across_clues = []
        down_clues = []
        for ws in puzzle.words:
            if ws.direction == 'across':
                across_clues.append((ws.number, ws.clue))
            else:
                down_clues.append((ws.number, ws.clue))
        self.across_scroll.clear_widgets()
        self.down_scroll.clear_widgets()
        self.across_scroll.add_widget(CluesList('ACROSS', across_clues))
        self.down_scroll.add_widget(CluesList('DOWN', down_clues))
        # Update header and buttons
        self.update_header()
        self.delete_btn.disabled = False
        self.pause_btn.disabled = False
        # Reset timer
        self.start_time = Clock.get_time()
        self.timer_running = True
        self.timer_label.text = 'Time: 00:00'
        
        for cell in self.current_grid.cells.values():
            cell.keyboard_on_key_down = self.make_keyboard_handler(cell)

    def on_new_puzzle(self, *args):
        self.load_new_puzzle()

    def on_delete_puzzle(self, *args):
        if self.current_puzzle:
            self.puzzle_store.delete_puzzle(self.current_puzzle)
            self.current_puzzle = None
            self.current_no = None
            # If store is now empty, show empty state
            if not self.puzzle_store.list_puzzles():
                self.display_empty_state()
            else:
                self.load_latest_puzzle()

    def on_pause_timer(self, *args):
        self.timer_running = not self.timer_running
        self.pause_btn.text = "Resume" if not self.timer_running else "Pause"

    def update_timer(self, dt):
        if not self.timer_running or self.start_time is None or not self.current_puzzle:
            return
        elapsed = int(Clock.get_time() - self.start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        self.timer_label.text = f'Time: {minutes:02d}:{seconds:02d}'

    def _on_keyboard_down(self, window, key, scancode, codepoint, modifier):
        pass

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

    def move_to_next_cell(self, current_cell):
        if current_cell.is_frozen:
            return
        current_row, current_col = current_cell.row, current_cell.col
        for word_idx in current_cell.word_ids:
            word_data = self.current_puzzle.words[word_idx]
            if word_idx in self.current_grid.words_completed:
                continue
            start_row, start_col = word_data.position
            direction = word_data.direction
            word_length = len(word_data.word)
            if direction == 'across':
                current_pos_in_word = current_col - start_col
                for offset in range(current_pos_in_word + 1, word_length):
                    next_pos = (current_row, start_col + offset)
                    if next_pos in self.current_grid.cells and not self.current_grid.cells[next_pos].is_frozen:
                        self.current_grid.cells[next_pos].focus = True
                        return
            else:
                current_pos_in_word = current_row - start_row
                for offset in range(current_pos_in_word + 1, word_length):
                    next_pos = (start_row + offset, current_col)
                    if next_pos in self.current_grid.cells and not self.current_grid.cells[next_pos].is_frozen:
                        self.current_grid.cells[next_pos].focus = True
                        return

    def move_to_previous_cell(self, current_cell):
        current_row, current_col = current_cell.row, current_cell.col
        for word_idx in current_cell.word_ids:
            word_data = self.current_puzzle.words[word_idx]
            if word_idx in self.current_grid.words_completed:
                continue
            start_row, start_col = word_data.position
            direction = word_data.direction
            if direction == 'across':
                current_pos_in_word = current_col - start_col
                if current_pos_in_word > 0:
                    for offset in range(current_pos_in_word - 1, -1, -1):
                        prev_pos = (current_row, start_col + offset)
                        if prev_pos in self.current_grid.cells and not self.current_grid.cells[prev_pos].is_frozen:
                            self.current_grid.cells[prev_pos].focus = True
                            self.current_grid.cells[prev_pos].text = ''
                            return
            else:
                current_pos_in_word = current_row - start_row
                if current_pos_in_word > 0:
                    for offset in range(current_pos_in_word - 1, -1, -1):
                        prev_pos = (start_row + offset, current_col)
                        if prev_pos in self.current_grid.cells and not self.current_grid.cells[prev_pos].is_frozen:
                            self.current_grid.cells[prev_pos].focus = True
                            self.current_grid.cells[prev_pos].text = ''
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
        if next_pos in self.current_grid.cells:
            self.current_grid.cells[next_pos].focus = True

    def on_word_complete(self, word_idx, is_correct):
        if is_correct:
            if len(self.current_grid.words_completed) == len(self.current_puzzle.words):
                self.show_congratulations()

    def show_congratulations(self):
        elapsed = int(Clock.get_time() - self.start_time) if self.start_time else 0
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
