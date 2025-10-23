from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from operator import itemgetter
import re
import bisect
import time
from typing import Optional
import random

# -----------------------
# Data domain model
# -----------------------

def generate_puzzle_id() -> str:
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = int((now - midnight).total_seconds())
    return f"{now.year:04d}{now.month:02d}{now.day:02d}{seconds_since_midnight:05d}"



# @dataclass
# class WordSpec:
#     word: str
#     clue: str
#     # starting first row and col
#     row: int = None
#     col: int = None
#     # 0='across', 1='down'
#     direction: int = None
    
# @dataclass
# class PuzzleSpec:
#     id: str = field(default_factory=generate_puzzle_id)
#     rows: int = 0
#     cols: int = 0
#     words: List[WordSpec] = field(default_factory=list)
#     # Puzzle sequential number stored/persisted in Store 
#     no: int = None

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


def count_chars(s: str) -> int:
    """Count letters in s, return (nb_chars, firstchar_pos, lastchar_pos)
    string s is expected to contain letters and '-' as fillable markers.
    """
    allchars_pos = [(m.span()[0]) for m in re.finditer(r'\w', s)]
    if len(allchars_pos) == 0:
        raise ValueError("No letters in string")
    
    return (len(allchars_pos), allchars_pos[0], allchars_pos[-1])


def get_regex(letter_seq: str):
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

def gen_patterns(letter_seq: str, pos): 
    """Generate all possible regex patterns holding at least one letter 
    from the given letter sequence, starting at position pos in grid 
    (i.e. where we can begin to fill the grid) 

    Args:
        letter_seq: letters pattern, e.g. '--R----G--E'
        pos: Position index in grid where letter_seq starts (row or col)
        
    Yields: Tuples of (pattern_regex, pos)
    """
    yield (get_regex(letter_seq), pos)
    nb_chars, first_char_pos, last_char_pos = count_chars(letter_seq)
    
    if nb_chars > 1:
        # trim "right":
        sub_seq = letter_seq[:last_char_pos-1]
        if len(sub_seq) > 1:
            yield from gen_patterns(sub_seq, pos=pos)
        # trim "left"
        new_pos = pos + first_char_pos + 2
        sub_seq = letter_seq[first_char_pos+2:]
        if len(sub_seq) > 1:
            yield from gen_patterns(sub_seq, pos=new_pos)


@dataclass(order=True)
class Word:
    word: str
    # as appear in grid (capital, non-accented, etc..)
    canonical: str = None
    clue: str = None
    # 0-based coordinates, top-left origin
    start_row: int = None
    start_col: int = None
    # 0=across, 1=down
    direction: int = None

    def __post_init__(self):
        # TODO: dev funt to remove accent and capitalize
        # as appearing in Grid
        self.canonical = self.word.upper()
        self.size = len(self.canonical)
    
    def place_word(self, row: int, col: int, direction: int):
        self.start_row = row
        self.start_col = col
        self.direction = direction
    
    def blocked_span(self, padding=False) -> tuple[int,int]:
        """Return blocked span of this word optionnally encompassing 
        one letter before and after the word itself (padding=True).
        """
        if self.start_row is None or self.start_col is None or self.direction is None:
            return None
        if self.direction == 0:  # across
            start = self.start_col - (1 if padding and self.start_col > 0 else 0)
            end = self.start_col + self.size + (1 if padding else 0)
        else:  # down
            start = self.start_row - (1 if padding and self.start_row > 0 else 0)
            end = self.start_row + self.size + (1 if padding else 0)
        return (start, end)
        
    
    def letter_at(self, cell_row, cell_col) -> str:
        """Return letter at given cell (row, col) if part of this word, else None.
        """
        if self.start_row and self.start_col and (self.direction in (0,1)):
            if self.direction == 0:  # across
                if cell_row == self.start_row and self.start_col <= cell_col < self.start_col + self.size:
                    return self.canonical[cell_col - self.start_col]
            else:  # down
                if cell_col == self.start_col and self.start_row <= cell_row < self.start_row + self.size:
                    return self.canonical[cell_row - self.start_row]



class Puzzle:
    def __init__(self, grid_size: int, available_words: list[tuple[str,str]]):
        """Initialize Puzzle instance.
        
        Args:
            grid_size: Size of grid (square grid_size x grid_size)
            available_words: List of tuples of (word, clue)
        """
        self.id: str = generate_puzzle_id()
        self.grid_size = grid_size      
        self.available_words: List[Word] = []
        self.min_size_word = self.grid_size
        for i, w in enumerate(available_words):
            if len(w[0]) < self.min_size_word:
                self.min_size_word = len(w[0])
            if len(w[0]) <= self.grid_size:
                self.available_words.append(Word(word=w[0], clue=w[1]))
        self.available_words.sort(key=lambda x: len(x.word), reverse=True)
        # '[3]WORDX[7]WORDY...'
        self.available_wordseq = ''.join([f"[{i}]{w.canonical}" for i, w in enumerate(self.available_words)])

        # puzzle number in store
        self.no: int = None
        
        # {direction: {col/row-index: [Wordx, ...]}}
        self.placed_words: Dict[int, Dict[int, List[Word]]] = {}
        # {direction: [col/row-indexes]}, initially all grid available
        self.blocked_indexes: dict[int:list[int]] = {0:[], 1:[]}


    def derive_letter_sequences(self, direction: int, index: int) -> tuple[list[str], list[str]]:
        """Derive letter sequences for given row/col index according to direction with '-' fillable markers, 
        '0' blocked markers, and 'L' letter from already perpendicular placed words.
        """
        frozen_spans = [w.blocked_span(padding=True) for w in self.placed_words.get(direction, {}).get(index, [])]
        left_frozen_spans = [w.blocked_span() for w in self.placed_words.get(direction, {}).get(index-1, [])]
        right_frozen_spans = [w.blocked_span() for w in self.placed_words.get(direction, {}).get(index+1, [])]

        # fillout cells with '-' (fillable marker)
        l_seq = ['-' for _ in range(self.grid_size)]
        # overwrite cells within blocked spans
        for span in frozen_spans + left_frozen_spans + right_frozen_spans:
            l_seq[span[0]:span[1]] = ['0' for _ in range(span[0], span[1])]

        # overwrite cells with letters from perpendicular words
        for i, l in enumerate(l_seq):
            if l == '-':
                index_c = index if direction == 1 else i
                index_r = i if direction == 1 else index
                letter_crossed = [w.letter_at(index_r, index_c) for w in self.placed_words.get(1 - direction, {}).get(i, []) if w.letter_at(index_r, index_c)]
                assert len(letter_crossed) <= 1
                if len(letter_crossed) == 1:
                    l_seq[i] = letter_crossed[0]

        return ''.join(l_seq)
 

    def fillout_grid(self):
        """Randonly select a next row or col, get its letter_sequence consecutive pattens
          and try to find a matching word
        
        Shoud probably prioritize the one with longest letter_seq available!!
        ..to be experimented!
        """
        
        # select randon col or row not in self.blocked_indexes
  
        # get letter sequence for that col/row --> self.derive_letter_sequences()

        # iterate over all possible patterns (skipping blocked spans)

            # if no patters larger in size than min_size_word --> add to self.complete_indexes
    
            # otherwise try to find a matching word in available_words, if no match for all possible pattern --> add to self.complete_indexes
        
            # if match found --> call self.place_word



    def find_matches(self, letter_seq: str) -> Optional[tuple[int, str]]:
        """Find and return first word fitting the row/col letter_seq

        Args:
            remaining_words: 
            where # indicates sequence number in self.available_words
            letter_seq: Letter sequence to fit for some row/col in grid'
        
        Returns:
            Tuples of (word_n, matched_word) where word_n is sequence# in available_words.
        """
        for p_regex in self.gen_patterns(letter_seq):
            match = re.search(p_regex, self.available_wordseq)
            if match:
                word_n = int(match.group(1))
                matched_word = match.group(2)
                return word_n, matched_word

    def place_word(self, word_n: int, row: int, col: int, direction: int):
        """Place word identified by word_n at given row, col, direction in grid.

        Args:
            word_n: Sequence number of word in available_words
            row: 0-based row index
            col: 0-based col index
            direction: 0=across, 1=down
        """
        word = self.available_words[word_n]
        word.place_word(row, col, direction)
        self.placed_words.setdefault(direction, {}).setdefault((col if direction==1 else row), []).append(word)
        # refresh available_wordseq 

        # refresh self.blocked_indexes according to row/col having no perpendicular words placed yet 


    # probably not needed
    def cell_status(self, row: int, col: int, direction):
        """Return status hint at given cell (row, col) according to direction:
        Returns:
        """
        # 1st check word in same direction        
        words_in_direction = self.placed_words.get(direction, {}).get(col if direction==1 else row, [])            
        for w in words_in_direction:
            if w.in_frozen_span(row, col):
                return 0
        # check if letter present from words in other direction
        other_direction = 1 - direction
        words_in_other_direction = self.placed_words.get(other_direction, {}).get(col if other_direction==1 else row, [])
        

            

            


def generate_grid_pattern(current_puzzle: Puzzle, direction: int):
    """Yield all possible pattern of next words locations in the grid

    Args:
        current_puzzle: Current Puzzle instance with words placed
        direction: 0=across, 1=down
    Yields:
        Tuples of (row, col, pattern) where pattern is a regex string
        from longest pattern to shortest.
    """
    pass




class PuzzleBuilder():
    def __init__(self, rows, cols, wordlist):
        self.rows = rows
        self.cols = cols
        self.min_size = min(rows, cols)
        wordlist.sort(key=len, reverse=True)
        self.wordlist_sorted = [Word(word=w) for w in wordlist if len(w) <= self.min_size]
        

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    

