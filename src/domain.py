from collections import defaultdict, namedtuple
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache, cached_property
from operator import itemgetter
import re
import bisect
import time
from typing import NamedTuple, Optional
import random
import enum


def generate_puzzle_id() -> str:
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = int((now - midnight).total_seconds())
    return f"{now.year:04d}{now.month:02d}{now.day:02d}{seconds_since_midnight:05d}"


def count_letters(s: str) -> int:
    """Count letters in s, return (nb_chars, firstchar_pos, lastchar_pos)
    string s is expected to contain letters and self.empty_marker (MUST NOT match regex \w)
    as fillable markers.
    """
    letters_pos = [(m.span()[0]) for m in re.finditer(r'\w', s)]
    if len(letters_pos) == 0:
        raise ValueError(f"No letter(s) in string={s}")
    
    return (len(letters_pos), letters_pos[0], letters_pos[-1])


def get_regex(letter_seq: str, empty_marker) -> str:
    """ Generate regex pattern string for a given letter sequence.
    Args:
        letter_seq: String of letters, e.g. '--R----G--E' (if empty_marker='-')
    Returns:
        Regex pattern string, e.g. r'\[(\d+)\](\w{0,2}R\w{4}G\w{2}E)\[(\d+)\]'
    """
    pfix = r'\[(\d+)\]'
    nb_c, firstc_pos, lastc_pos = count_letters(letter_seq)

    if firstc_pos > 0:
        left_opt_c = r'(\w{0,' + str(firstc_pos) + '}'
        result_list = [pfix, left_opt_c, ]
    else:
        result_list = [pfix, '(', ]

    counter_empty = 0
    for i in range(firstc_pos, lastc_pos + 1):
        if letter_seq[i] == empty_marker:
            counter_empty += 1
        else:
            if counter_empty > 0:
                result_list.append(r'\w{' + str(counter_empty) + '}')
            result_list.append(letter_seq[i])
            counter_empty = 0

    if lastc_pos < len(letter_seq) - 1:
        right_opt_c = r'\w{0,' + str(len(letter_seq)-1-lastc_pos) + '})'
        result_list.append(right_opt_c)
    else:
        result_list.append(')')
    result = ''.join(result_list) + pfix
    return result

def gen_patterns(letter_seq: str, pos, min_size, empty_marker='-'): 
    """Generate all regex patterns and sub-patterns from letter_seq 
    (with 1 or more letters) of size larger or equal to min_size.
    Where pos indicates position in grid 

    Args:
        letter_seq: letters pattern, e.g. '--R----G--E'
        pos: Position index in grid where letter_seq starts (row or col)
        
    Yields: Tuples of (pattern_regex, pos)
    """
    nb_chars, first_char_pos, last_char_pos = count_letters(letter_seq)
    if len(letter_seq) < min_size:
        return
    
    yield (get_regex(letter_seq, empty_marker), pos)
    
    # generate recursively sub-patterns
    if nb_chars > 1:
        # trim "right":
        sub_seq = letter_seq[:last_char_pos-1]
        if len(sub_seq) > 1:
            yield from gen_patterns(sub_seq, pos, min_size)
        # trim "left"
        new_pos = pos + first_char_pos + 2
        sub_seq = letter_seq[first_char_pos+2:]
        if len(sub_seq) > 1:
            yield from gen_patterns(sub_seq, new_pos, min_size)


# -----------------------
# Data domain model
# -----------------------

class Location(NamedTuple):
    direction : int
    index : int


@dataclass(order=True)
class Word:
    word: str
    # as appear in grid (capital, non-accented, etc..)
    canonical: str = field(default=None, compare=False)
    clue: str = field(default=None, compare=False)
    # 0-based coordinates, top-left origin
    row: int = field(default=None, compare=False)
    col: int = field(default=None, compare=False)
    # 0=across, 1=down
    direction: int = field(default=None, compare=False)

    def __post_init__(self):
        # TODO: dev funt to remove accent and capitalize
        # as appearing in Grid
        self.canonical = self.word.upper()
        self.size = len(self.canonical)
    
    def set_position(self, location: Location, pos: int):
        self.direction = location.direction
        if location.direction == 1:
            self.row = pos
            self.col = location.index
        else:
            self.row = location.index
            self.col = pos

        
        
    
    # @cache TODO: test fail when using cache decorator
    def span(self, padding=False) -> list[int]:
        """Return blocked span of this word as list[start-index, end-index] both inclusive. 
        Use padding=True to include one cell before and after the word itself.
        """
        if self.direction == 0:
            start = self.col - (1 if padding and self.col > 0 else 0)
            end = self.col + self.size - 1 + (1 if padding else 0)
            return list(range(start, end+1))
        elif self.direction == 1:
            start = self.row - (1 if padding and self.row > 0 else 0)
            end = self.row + self.size - 1 + (1 if padding else 0)
            return list(range(start, end+1))
    
       
    def letter_at(self, cell_row: int, cell_col: int) -> str:
        """Return letter at given cell (row, col) if part of this word, else None.
        """
        if self.direction == 0:  # across
            if cell_row == self.row and self.col <= cell_col < self.col + self.size:
                return self.canonical[cell_col - self.col]
        elif self.direction == 1:  # down
            if cell_col == self.col and self.row <= cell_row < self.row + self.size:
                return self.canonical[cell_row - self.row]


class Puzzle:
    def __init__(self, grid_size: int, words: list[tuple[str,str]]):
        """Initialize Puzzle instance.
        
        Args:
            grid_size: Size of grid (square grid_size x grid_size)
            available_words: List of tuples of (word, clue)
        """
        self.id: str = generate_puzzle_id()
        self.grid_size = grid_size      
        self.available_words: list[Word] = []
        self.min_size_word = self.grid_size
        for i, w in enumerate(words):
            if len(w[0]) < self.min_size_word:
                self.min_size_word = len(w[0])
            if len(w[0]) <= self.grid_size:
                self.available_words.append(Word(word=w[0], clue=w[1]))
        self.available_words.sort(key=lambda x: len(x.word), reverse=True)
        # '[3]WORDX[7]WORDY...'
        self.available_wordseq = ''.join([f"[{i}]{w.canonical}" for i, w in enumerate(self.available_words)])

        self.placed_words: dict[Location, list[Word]] = {}
        self.nb_placed_words = 0
        
        self.empty_marker='-'
        self.filled_marker='#'
        
        # convenient structures
        self.grid = [[self.empty_marker for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        # No word can fit these row/col Adresses  (no space left)
        self.complete_indexes: set[Location] = set() 
        # No Word and letter present on these row/col Adresses to attach word
        self.empty_indexes: set[Location] = { Location(direction=d, index=i) for d in [0,1] for i in range(self.grid_size)} 
    
    def _get_entirepattern(self, loc: Location) -> str:
        """Derive text pattern for the entire row/col (given by index and direction), 
        with empty markers, filled markers and letter from perpendicular placed words.
        """
        if loc.direction == 0:
            pattern = [self.grid[loc.index][c] for c in range(self.grid_size)]
        else:
            pattern = [self.grid[r][loc.index] for r in range(self.grid_size)]

        # block cell from words placed in direction on same col/row (index)
        block_cells = [ cells for w in self.placed_words.get(loc, []) for cells in w.span(padding=True)]
        
        # block cell from words on "left" col/row 
        left_spans = []
        if loc.index > 0:
            left_adress = Location(loc.direction, loc.index - 1)
            left_spans = [ cells for w in self.placed_words.get(left_adress, []) for cells in w.span()]

        # block cell from words on "right" col/row'
        right_spans = []
        if loc.index < self.grid_size - 1:
            right_adress = Location(loc.direction, loc.index + 1)
            right_spans = [ cells for w in self.placed_words.get(right_adress, []) for cells in w.span() ]

        # go over each cell in fullpattern and mark blocked ones
        for cell_i in range(self.grid_size):
            if cell_i in block_cells:
                pattern[cell_i] = self.filled_marker
            elif pattern[cell_i] == self.empty_marker:
                # left/right spans only block when no letter present (from perpendicular placed words)
                if cell_i in left_spans or cell_i in right_spans:
                    pattern[cell_i] = self.filled_marker
                # block also cell neighbor of an end/start of a word placed perpendicularly
                if loc.direction == 1:
                    # "left"
                    if loc.index >= 2 and self.grid[cell_i][loc.index-1] != self.empty_marker: 
                        pattern[cell_i] = self.filled_marker
                    # "right"
                    elif loc.index <= self.grid_size - 3 and self.grid[cell_i][loc.index+1] != self.empty_marker:
                        pattern[cell_i] = self.filled_marker
                else:  # direction == 0
                    # "left"
                    if loc.index >= 2 and self.grid[loc.index-1][cell_i] != self.empty_marker: 
                        pattern[cell_i] = self.filled_marker
                    # "right"
                    elif loc.index <= self.grid_size - 3 and self.grid[loc.index+1][cell_i] != self.empty_marker:
                        pattern[cell_i] = self.filled_marker
        return ''.join(pattern)


    def _get_subpatterns(self, loc: Location) -> list[tuple[str,int]]:
        """
        """
        
        entirepattern = self._get_entirepattern(loc)

        letter_sequences : list[tuple[str,int]] = []
        # Add consecutive subpatterns of minimum size 2
        for s in entirepattern.split(self.filled_marker):
            # accept long enough pattern and having at least one letter
            if len(s) >= 2:
                letter_sequences.append((s,entirepattern.index(s)))
        
        # return tuple of (sub-pattern, position) sorted from largest to smallest in length
        return sorted(letter_sequences, key=lambda x: len(x[0]), reverse=True)


    def fillout(self, timeout: int = 60):
        """Randonly select a not empty and not filled row or col, get its letter_sequence consecutive pattens
          and try to find a matching word
        
        Shoud probably prioritize the one with longest letter_seq available!!
        ..to be experimented!
        """
        start_time = time.time()
        iter, iter_skip = 0, 0
        self.place_first_word()
        
        self.currently_blocked = set()
        # randomly fill out rows/cols
        while True:
            iter += 1
            selection = self.next_selection(self.currently_blocked)

            if selection[0] < 0:
                self.elapse_time = time.time()-start_time
                print(f"Fillout completed in {self.elapse_time:.2f} sec! #iterations={iter} (#skips={iter_skip})! --> {selection[1]}")
                break
            
            the_direction = selection[0]
            the_index = selection[1]
            letter_seqs = self._get_subpatterns(the_direction, the_index)

            # skip when currently blocked
            if letter_seqs == -3:
                self.currently_blocked.add(selection)
                iter_skip += 1
                continue
            # current selection turn out to be complete
            elif letter_seq == -1 or len(letter_seqs) == 0:
                self.mark_as_complete(the_direction, the_index)
                continue  

            for letter_seq in letter_seqs:
                match = self.find_matches(letter_seq[0])
                if match:
                    word_n, matched_word = match
                    # TODO: revalidate the letter_seq[1] as word may not start at beginning of letter_seq!!
                    row, col = (the_index, letter_seq[1]) if the_direction == 0 else (letter_seq[1], the_index)
                    self.place_word(word_n, row, col, the_direction)
                    self.currently_blocked.clear()
                    break

            if not match:
                self.mark_as_complete(the_direction, the_index)
                

    def next_selection(self, currently_blocked: set):
        """
        Selects the next row or column index for placing a word, considering certain conditions.
        Args:
            currently_blocked: A list of row/column indices that are temporarily blocked 

        Returns:
            tuple:
                - If a stop condition is met, returns a tuple with a negative integer and a string 
                  message explaining the stop condition:
                    - (-2, 'Stop condition: no more words to select from'): All words have been placed.
                    - (-1, 'Stop condition: all row/col either completed or empty'): No row/column available.
                    - (-3, 'Stop condition: Available row/col are all blocked'): Available row/column all currently_blocked
                - Otherwise, returns a randomly selected tuple (direction, index) where:
                    - direction (int): 0 for rows, 1 for columns.
                    - index (int): The selected row or column index.
        
        """
        # Stop Condition -2 
        if self.nb_placed_words == len(self.available_words):
            return (-2, 'Stop condition: no more words to select from')

        available_choices = {(d,i) for d in random.randint(0,1) for i in range(self.grid_size) 
                                if i not in self.complete_indexes[d] and 
                                   i not in self.empty_indexes[d]}
        
        # Stop Condition -1: all row/col either completed or empty  
        if len(available_choices) == 0:
            return (-1, 'Stop condition: all row/col either completed or empty')
        
        # Stop Condition -3 
        if available_choices == currently_blocked:
            return (-3, 'Stop condition: Available row/col are all currently blocked')
        
        return random.choice(available_choices)    


    def _is_blocked(self, subpatterns: list[tuple[str,int]]):
        for p in subpatterns:
            assert p.count(self.filled_marker) == 0
            if p.count(self.empty_marker) < len(p):
                return False
        return True
    
    def _is_complete(self, subpatterns: list[tuple[str,int]]):
        """ True if all subpatterns are too short to fit smallest word in self.available_words
        """
        if len(subpatterns) == 0:
            return True

        for p in subpatterns:
            assert p.count(self.filled_marker) == 0
            if len(p) >= len(self.min_size_word):
                return False
        return True


    def find_matches(self, letter_seq: str) -> Optional[tuple[int, str]]:
        """Find and return first word fitting the row/col letter_seq

        Args: 
            letter_seq: Letter sequence to match for some row/col in grid'
        
        Returns:
            Tuples of (word_n, matched_word) where word_n is sequence# in available_words.
        """
        for p_regex in self.gen_patterns(letter_seq):
            match = re.search(p_regex, self.available_wordseq)
            if match:
                word_n = int(match.group(1))
                matched_word = match.group(2)
                return word_n, matched_word

    def place_first_word(self, word_index: int = None, loc: Location = None, pos: int = None):
        """"Place first word (at index word_i in avalable_words) at adress and pos, when not provided 
        pick randomly top-5 longest word and location
        """
        if self.nb_placed_words == 0:
            if not word_index:
                # use first 5 longest words
                word_index = random.randint(0, 4)

            first_w_len = len(self.available_words[word_index].canonical)
            assert first_w_len <= self.grid_size

            if not loc:
                loc = Location(random.choice([0,1]), index=random.randint(0, self.grid_size - 1))
                pos = random.randint(0, self.grid_size - first_w_len)
            
            self.place_word(word_index=word_index, loc=loc, pos=pos)

    def place_word(self, word_index: int, loc: Location, pos: int):
        """Place word identified by word_n at given row, col, direction in grid.

        Args:
            word_n: Sequence number of word in available_words
            row: 0-based row index
            col: 0-based col index
            direction: 0=across, 1=down
        """
        word = self.available_words[word_index]
        word.set_position(location=loc, pos=pos)
        self.placed_words.setdefault(loc, []).append(word)
        self.nb_placed_words += 1
        self.refresh_structures(word, word_index, loc, pos)

        return word


    def refresh_structures(self, word: Word, word_index: int, loc: Location, pos: int):

        # grid
        for i in range(word.size):
            if loc.direction == 0:
                self.grid[loc.index][pos + i] = word.canonical[i]
            else:
                self.grid[pos+i][loc.index] = word.canonical[i]

        # available_wordseq 
        s_index = self.available_wordseq.index(f'[{word_index}]')
        e_index = self.available_wordseq.find('[', s_index+1)
        if e_index == -1:
            e_index = len(self.available_wordseq)
        self.available_wordseq = self.available_wordseq[:s_index] + self.available_wordseq[e_index:]
                
        # self.empty_indexes
        self.empty_indexes.difference_update({Location(direction=1-loc.direction, index=i) for i in word.span()})
        
        # self.complete_indexes on current index
        if self._is_complete(self._get_subpatterns(loc)):
            self.complete_indexes.add(loc)
        # on "left index"
        if loc.index > 0:
            left_loc = Location(loc.direction, index=loc.index-1)
            if self._is_complete(self._get_subpatterns(left_loc)):
                self.complete_indexes.add(left_loc)
        # on "right index"
        if loc.index < self.grid_size - 1:
            right_loc = Location(loc.direction, index=loc.index+1)
            if self._is_complete(self._get_subpatterns(right_loc)):
                self.complete_indexes.add(right_loc)

    
    def stats_info(self):
        return {'Nb of words': self.nb_placed_words, 'Elapse time': self.elapse_time }
    
    def __str__(self):
        return '\n'.join([' '.join(row) for row in self.grid])

#     def to_dict(self):
#         return {
#             "id": self.id,
#             "rows": self.rows,
#             "cols": self.cols,
#             "words": [w.__dict__ for w in self.words]
#         }

#     @staticmethod
#     def from_dict(data):
#         return PuzzleSpec(
#             id=data["id"],
#             rows=data["rows"],
#             cols=data["cols"],
#             words=[WordSpec(**w) for w in data["words"]]
#         )




        

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    

