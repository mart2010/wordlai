from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache, cached_property
from operator import itemgetter
import re
import bisect
import time
from typing import Optional
import random

def generate_puzzle_id() -> str:
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = int((now - midnight).total_seconds())
    return f"{now.year:04d}{now.month:02d}{now.day:02d}{seconds_since_midnight:05d}"


def count_chars(s: str) -> int:
    """Count letters in s, return (nb_chars, firstchar_pos, lastchar_pos)
    string s is expected to contain letters and '-' as fillable markers.
    """
    allchars_pos = [(m.span()[0]) for m in re.finditer(r'\w', s)]
    if len(allchars_pos) == 0:
        raise ValueError("No letters in string")
    
    return (len(allchars_pos), allchars_pos[0], allchars_pos[-1])


def get_regex(letter_seq: str) -> str:
    """ Generate regex pattern string for a given letter sequence.
    Args:
        letter_seq: String of letters, e.g. '--R----G--E'
    Returns:
        Regex pattern string, e.g. r'\[(\d+)\](\w{0,2}R\w{4}G\w{2}E)\[(\d+)\]'
    """
    pfix = r'\[(\d+)\]'
    nb_c, firstc_pos, lastc_pos = count_chars(letter_seq)

    if firstc_pos > 0:
        left_opt_c = r'(\w{0,' + str(firstc_pos) + '}'
        result_list = [pfix, left_opt_c, ]
    else:
        result_list = [pfix, '(', ]

    counter_dash = 0
    for i in range(firstc_pos, lastc_pos + 1):
        if letter_seq[i] == '-':
            counter_dash += 1
        else:
            if counter_dash > 0:
                result_list.append(r'\w{' + str(counter_dash) + '}')
            result_list.append(letter_seq[i])
            counter_dash = 0

    if lastc_pos < len(letter_seq) - 1:
        right_opt_c = r'\w{0,' + str(len(letter_seq)-1-lastc_pos) + '})'
        result_list.append(right_opt_c)
    else:
        result_list.append(')')
    result = ''.join(result_list) + pfix
    return result

def gen_patterns(letter_seq: str, pos, min_size): 
    """Generate all regex patterns and sub-patterns from letter_seq 
    (with 1 or more letters) of size larger or equal to min_size.
    Where pos indicates position in grid 

    Args:
        letter_seq: letters pattern, e.g. '--R----G--E'
        pos: Position index in grid where letter_seq starts (row or col)
        
    Yields: Tuples of (pattern_regex, pos)
    """
    nb_chars, first_char_pos, last_char_pos = count_chars(letter_seq)
    if len(letter_seq) < min_size:
        return
    
    yield (get_regex(letter_seq), pos)
    
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
    
    def set_position(self, row: int, col: int, direction: int):
        self.row = row
        self.col = col
        self.direction = direction
    
    # @cache TODO: test fail when using cache decorator
    def blocked_span(self, padding=False) -> list[int]:
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
    
       
    def letter_at(self, cell_row, cell_col) -> str:
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

        # {direction: {col/row-index: [Wordx, ...]}}
        self.placed_words: dict[int, dict[int, list[Word]]] = {}
        self.nb_placed_words = 0
        
        # convenient structures
        self.grid = [['-' for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        # No word fit in remaining patterns (either no match or full)
        self.complete_indexes: dict[int:list[int]] = {0:[], 1:[]}
        # No letter present on entire row/col to attach word
        self.empty_indexes: dict[int:list[int]] = {0:list(range(self.grid_size)), 
                                                   1:list(range(self.grid_size))}
    
    def _get_fullpattern(self, direction: int, index: int):
        """Derive full pattern for given row/col index and direction, 
        with '-' fillable markers, '0' blocked markers, and 'X' letter from perpendicular placed words.
        """
        if direction == 0:
            fullpattern = [self.grid[index][c] for c in range(self.grid_size)]
        else:
            fullpattern = [self.grid[r][index] for r in range(self.grid_size)]

        if fullpattern.count('-') == self.grid_size or fullpattern.count('-') == 0:
            raise Exception("Unexpected pattern in direction {}, index {}".format(direction, index))

        # block cell from words placed in this direction on same col/row (index) marked as '0'
        block_cells = [ cells for w in self.placed_words.get(direction, {}).get(index, []) for cells in w.blocked_span(padding=True)]
        # block cell from words "left" col/row 
        left_spans = [ cells for w in self.placed_words.get(direction, {}).get(index-1, []) for cells in w.blocked_span() if index > 0 ]
        # block cell from words on "rigt" col/row'
        right_spans = [ cells for w in self.placed_words.get(direction, {}).get(index+1, []) for cells in w.blocked_span() if index < self.grid_size - 1 ]

        # go over each cell in fullpattern and mark blocked ones as '0'
        for cell_i in range(self.grid_size):
            if cell_i in block_cells:
                fullpattern[cell_i] = '0'
            elif fullpattern[cell_i] == '-':
                # left/right spans only block when no letter present (from perpendicular placed words)
                if cell_i in left_spans or cell_i in right_spans:
                    fullpattern[cell_i] = '0'
                # block also cell neighbor of an end/start of a word placed perpendicularly
                if direction == 1:
                    # "left"
                    if index >= 2 and self.grid[cell_i][index-1] != '-': 
                        fullpattern[cell_i] = '0'
                    # "right"
                    elif index <= self.grid_size - 3 and self.grid[cell_i][index+1] != '-':
                        fullpattern[cell_i] = '0'
                else:  # direction == 0
                    # "left"
                    if index >= 2 and self.grid[index-1][cell_i] != '-': 
                        fullpattern[cell_i] = '0'
                    # "right"
                    elif index <= self.grid_size - 3 and self.grid[index+1][cell_i] != '-':
                        fullpattern[cell_i] = '0'
        return ''.join(fullpattern)


    def get_letter_sequences(self, direction: int, index: int) -> list[tuple[str,int]]:
        
        fullpattern = self._get_fullpattern(direction, index)
        nb_empty = fullpattern.count('-')
        nb_busy = fullpattern.count('0')

        # Intercept early these exceptins
        # col/row is complete
        if self.grid_size - nb_busy < self.min_size_word:
            return -1 
        # currently blocked because no letter perp. exist in sequence
        if nb_empty + nb_busy == self.grid_size:
            return -3


        letter_sequences : list[tuple[str,int]] = []
        # split into seq of consecutive '-' and letter 'X' sub-patterns (unblocked) of min size     
        for s in fullpattern.split('0'):
            # accept long enough pattern and having at least one letter
            if self.min_size_word <= len(s) > s.count('-'):
                letter_sequences.append((s,fullpattern.index(s)))
        
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
            letter_seqs = self.get_letter_sequences(the_direction, the_index)

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


    def mark_as_complete(self, direction, index):
            assert index not in self.complete_indexes[direction]
            assert index not in self.empty_indexes[direction]
            self.complete_indexes[direction].append(index)


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

    def place_first_word(self):
        """"place first word pickin randomly top-5 longest word
        """
        if self.nb_placed_words == 0:
            # use first 5 longest words  
            first_w_i = random.randint(0, 4)
            first_w_len = len(self.available_words[first_w_i].canonical)
            assert first_w_len <= self.grid_size
            index = random.randint(0, self.grid_size - 1)
            other_index = random.randint(0, self.grid_size - first_w_len)
            direction = random.choice([0,1])
            if direction == 0:
                self.place_word(word_n=first_w_i, row=index, col=other_index, direction=direction)
            else:
                self.place_word(word_n=first_w_i, row=other_index, col=index, direction=direction)


    def place_word(self, word_n: int, row: int, col: int, direction: int):
        """Place word identified by word_n at given row, col, direction in grid.

        Args:
            word_n: Sequence number of word in available_words
            row: 0-based row index
            col: 0-based col index
            direction: 0=across, 1=down
        """
        word = self.available_words[word_n]
        word.set_position(row, col, direction)
        self.placed_words.setdefault(direction, {}).setdefault((col if direction==1 else row), []).append(word)
        self.nb_placed_words += 1

        # update grid
        for i in range(word.size):
            if direction == 0:
                self.grid[row][col + i] = word.canonical[i]
            else:
                self.grid[row + i][col] = word.canonical[i]

        # refresh available_wordseq 
        s_index = self.available_wordseq.index(f'[{word_n}]')
        e_index = self.available_wordseq.find('[', s_index+1)
        if e_index == -1:
            e_index = len(self.available_wordseq)
        self.available_wordseq = self.available_wordseq[:s_index] + self.available_wordseq[e_index:]
        # refresh self.empty_indexes
        self.empty_indexes[1-direction] = [i for i in self.empty_indexes[1-direction] if i not in word.blocked_span() ]
        return word
    
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
    

