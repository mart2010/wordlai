from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Set
import random

# -----------------------
# Data domain model
# -----------------------

def generate_puzzle_id() -> str:
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = int((now - midnight).total_seconds())
    return f"{now.year:04d}{now.month:02d}{now.day:02d}{seconds_since_midnight:05d}"

@dataclass
class WordSpec:
    word: str
    clue: str
    position: Tuple[int, int] = None  # (row, col) 1-based coordinates
    direction: str = None             # 'across' or 'down'
    number: int = 0

@dataclass
class Puzzle:
    id: str = field(default_factory=generate_puzzle_id)
    rows: int = 0
    cols: int = 0
    words: List[WordSpec] = field(default_factory=list)
    # Puzzle sequential number stored/persisted in Store 
    no: int = None

    def to_dict(self):
        return {
            "id": self.id,
            "rows": self.rows,
            "cols": self.cols,
            "words": [w.__dict__ for w in self.words]
        }

    @staticmethod
    def from_dict(data):
        return Puzzle(
            id=data["id"],
            rows=data["rows"],
            cols=data["cols"],
            words=[WordSpec(**w) for w in data["words"]]
        )


def generate_crossword_puzzle(
    word_clue_list: List[Tuple[str, str]],
    orientation: str = "portrait"
) -> Tuple[Puzzle, List[str]]:
    """
    Generate a sparse crossword puzzle from a list of (word, clue) tuples.
    - orientation: "portrait" or "landscape"
    Returns: (Puzzle, excluded_words)
    """
    # Normalize words to uppercase, remove duplicates
    word_clue_list = [(w.upper(), c) for w, c in word_clue_list]
    words = [w for w, _ in word_clue_list]
    clues = dict(word_clue_list)
    used_words: Set[str] = set()
    placed_words: List[WordSpec] = []
    excluded_words: List[str] = []

    # Start with the longest word in the center
    words_sorted = sorted(words, key=lambda w: -len(w))
    if not words_sorted:
        return Puzzle(0, 0, []), []

    # Grid size guess (will expand as needed)
    max_word_len = max(len(w) for w in words_sorted)
    grid_w = grid_h = max(2 * max_word_len, 10)
    grid = [['' for _ in range(grid_w)] for _ in range(grid_h)]
    offset_r = offset_c = grid_w // 2

    # Place the first word horizontally in the middle
    first_word = words_sorted[0]
    start_r = offset_r
    start_c = offset_c - len(first_word) // 2
    for i, ch in enumerate(first_word):
        grid[start_r][start_c + i] = ch
    placed_words.append(
        WordSpec(
            word=first_word,
            clue=clues[first_word],
            position=(start_r + 1, start_c + 1),
            direction='across',
            number=1
        )
    )
    used_words.add(first_word)

    # Helper: find all positions of a letter in the grid
    def find_letter_positions(letter):
        positions = []
        for r in range(grid_h):
            for c in range(grid_w):
                if grid[r][c] == letter:
                    positions.append((r, c))
        return positions

    # Cell orientations: (row, col): set of orientations ('across', 'down')
    cell_orientations = {}

    # Place remaining words
    word_number = 2
    for word in words_sorted[1:]:
        best = None  # (score, row, col, direction, cross_idx, word_idx)
        for direction in ['across', 'down']:
            for idx, ch in enumerate(word):
                positions = find_letter_positions(ch)
                for (r, c) in positions:
                    if direction == 'across':
                        start_r = r
                        start_c = c - idx
                        if start_c < 0 or start_c + len(word) > grid_w:
                            continue
                        # Check for conflicts and at least one crossing
                        conflict = False
                        crossing = False
                        crossing_count = 0
                        for i, letter in enumerate(word):
                            rr = start_r
                            cc = start_c + i
                            cell = grid[rr][cc]
                            cell_orient = cell_orientations.get((rr, cc), set())
                            if cell == '':
                                # Check for adjacent word (no two words side by side)
                                if (cc > 0 and grid[rr][cc-1] != '') or (cc < grid_w-1 and grid[rr][cc+1] != ''):
                                    if i == 0 or i == len(word)-1:
                                        pass  # allow at ends
                                    else:
                                        conflict = True
                                        break
                                if (rr > 0 and grid[rr-1][cc] != '') or (rr < grid_h-1 and grid[rr+1][cc] != ''):
                                    pass  # allow vertical adjacency
                            elif cell != letter:
                                conflict = True
                                break
                            else:
                                # Already occupied: must be a crossing with the other orientation
                                if direction in cell_orient:
                                    conflict = True
                                    break
                                crossing = True
                                crossing_count += 1
                        if not conflict and crossing and crossing_count == 1:
                            # Score: more crossings is better, more compact is better
                            score = 1  # Only one crossing allowed
                            if best is None:
                                best = (score, start_r, start_c, 'across', idx)
                    else:  # down
                        start_r = r - idx
                        start_c = c
                        if start_r < 0 or start_r + len(word) > grid_h:
                            continue
                        conflict = False
                        crossing = False
                        crossing_count = 0
                        for i, letter in enumerate(word):
                            rr = start_r + i
                            cc = start_c
                            cell = grid[rr][cc]
                            cell_orient = cell_orientations.get((rr, cc), set())
                            if cell == '':
                                if (rr > 0 and grid[rr-1][cc] != '') or (rr < grid_h-1 and grid[rr+1][cc] != ''):
                                    if i == 0 or i == len(word)-1:
                                        pass
                                    else:
                                        conflict = True
                                        break
                                if (cc > 0 and grid[rr][cc-1] != '') or (cc < grid_w-1 and grid[rr][cc+1] != ''):
                                    pass
                            elif cell != letter:
                                conflict = True
                                break
                            else:
                                if direction in cell_orient:
                                    conflict = True
                                    break
                                crossing = True
                                crossing_count += 1
                        if not conflict and crossing and crossing_count == 1:
                            score = 1
                            if best is None:
                                best = (score, start_r, start_c, 'down', idx)
        if best:
            _, r, c, direction, _ = best
            if direction == 'across':
                for i, letter in enumerate(word):
                    grid[r][c + i] = letter
                    cell_orientations.setdefault((r, c + i), set()).add('across')
                placed_words.append(
                    WordSpec(
                        word=word,
                        clue=clues[word],
                        position=(r + 1, c + 1),
                        direction='across',
                        number=word_number
                    )
                )
            else:
                for i, letter in enumerate(word):
                    grid[r + i][c] = letter
                    cell_orientations.setdefault((r + i, c), set()).add('down')
                placed_words.append(
                    WordSpec(
                        word=word,
                        clue=clues[word],
                        position=(r + 1, c + 1),
                        direction='down',
                        number=word_number
                    )
                )
            used_words.add(word)
            word_number += 1
        else:
            excluded_words.append(word)

    # Find bounds of used grid
    min_r, max_r, min_c, max_c = grid_h, 0, grid_w, 0
    for r in range(grid_h):
        for c in range(grid_w):
            if grid[r][c] != '':
                min_r = min(min_r, r)
                max_r = max(max_r, r)
                min_c = min(min_c, c)
                max_c = max(max_c, c)
    # Adjust for orientation
    if orientation == "landscape" and (max_r - min_r) > (max_c - min_c):
        # Transpose grid (not implemented for simplicity)
        pass

    # Shift all positions so top-left is (1,1)
    for ws in placed_words:
        ws.position = (ws.position[0] - min_r, ws.position[1] - min_c)

    rows = max_r - min_r + 1
    cols = max_c - min_c + 1

    # Renumber clues in reading order
    placed_words.sort(key=lambda ws: (ws.position[0], ws.position[1]))
    for idx, ws in enumerate(placed_words, 1):
        ws.number = idx

    return Puzzle(rows=rows, cols=cols, words=placed_words), excluded_words



def generate_words_clues(
    num_words: int,
    language: str,
    theme: str,
    difficulty: str,
    llm_endpoint: str,
    api_key: str = None
) -> List[Dict[str, str]]:
    """
    Returns: List of dicts: [{'word': ..., 'clue': ...}, ...]
    """
    # TODO: Implement LLM call with prompt and parameters
    pass


def mock_generate_words_clues(num_words: int) -> List[Dict[str, str]]:
    """
    Generate mock English words and dummy clues for testing.
    """
    word_list = [
        "python", "kivy", "crossword", "puzzle", "grid", "clue", "letter", "cell",
        "row", "column", "theme", "logic", "random", "sample", "word", "test",
        "input", "output", "button", "label", "window", "screen", "color", "store",
        "data", "event", "focus", "timer", "widget", "layout", "scroll", "popup",
        "float", "box", "app", "main", "domain", "service", "ai", "generate",
        "validate", "solution", "orientation", "number", "length", "phone", "desktop",
        "storage", "history", "previous", "view", "finish", "help", "select", "randomize",
        "difficulty", "theme", "language", "english", "advanced", "basic", "intermediate",
        "challenge", "fun", "play", "game", "user", "interface", "design", "screen",
        "touch", "keyboard", "mouse", "click", "highlight", "hint", "score", "time",
        "record", "save", "load", "delete", "list", "entry", "field", "value", "dict",
        "store", "json", "file", "open", "close", "read", "write", "update", "remove",
        "logic", "matrix", "vector", "object", "method", "class", "function", "module",
        "package", "import", "export", "compile", "run", "execute", "thread", "process",
        "memory", "cache", "buffer", "stream", "socket", "network", "protocol", "server",
        "client", "request", "response", "route", "path", "url", "http", "https", "ftp",
        "ssh", "encrypt", "decrypt", "secure", "token", "auth", "login", "logout", "session",
        "cookie", "header", "body", "json", "xml", "yaml", "csv", "parse", "serialize",
        "deserialize", "encode", "decode", "compress", "decompress", "archive", "extract"
    ]

    # Filter for length and uniqueness
    filtered = [w for w in set(word_list) if 3 <= len(w) <= 25]
    if len(filtered) < num_words:
        num_words = len(filtered)
    selected = random.sample(filtered, num_words)

    # Return as list of dicts with dummy clues
    return [{"word": w.upper(), "clue": f"Dummy clue for {w}."} for w in selected]

