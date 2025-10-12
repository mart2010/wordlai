import argparse
from collections import defaultdict
from operator import itemgetter
import random
import time

class ComplexString(str):
    """Handle accents and superscript / subscript characters."""
    accents = [768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781,
               782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795,
               796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809,
               810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823,
               824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837,
               838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851,
               852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865,
               866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879,
               2306, 2366, 2367, 2368, 2369, 2370, 2371, 2372, 2375, 2376, 2379,
               2380, 2402, 2403, 2433, 2492, 2494, 2495, 2496, 2497, 2498, 2499,
               2500, 2503, 2504, 2507, 2508, 2519, 2530, 2531, 3006, 3007, 3008,
               3009, 3010, 3014, 3015, 3016, 3018, 3019, 3020, 3021, 3031, 3633,
               3636, 3637, 3638, 3639, 3640, 3641, 3655, 3656, 3657, 3658, 3659,
               3660, 3661, 3662, 4139, 4140, 4141, 4142, 4143, 4144, 4145, 4146,
               4150, 4151, 4152, 4154, 4155, 4156, 4157, 4158, 4182, 4185]

    special_chars = [2381, 2509, 4153]

    @staticmethod
    def _check_special(word, special):
        special_char = False
        formatted = []
        for letter in word:
            if letter in special or special_char:
                special_char = not special_char
                formatted[-1] += letter
                continue
            formatted.append(letter)
        return formatted

    @staticmethod
    def format_word(word):
        """Join the accent to the character it modifies.
        This guarantees that the character is correctly displayed when
        iterating through the string, and that the length is correct.
        """
        chars = {chr(n) for n in ComplexString.accents}
        special = {chr(n) for n in ComplexString.special_chars}
        formatted = []
        for letter in word:
            if letter in chars:
                formatted[-1] += letter
                continue
            formatted.append(letter)
        if special.intersection(word):
            return ComplexString._check_special(formatted, special)
        return formatted

    def __new__(cls, content):
        cs = super().__new__(cls, content)
        cs.blocks = cls.format_word(content)
        return cs

    def __iter__(self):
        for block in self.blocks:
            yield block

    def __len__(self):
        return len(self.blocks)
    

class Genxword(object):
    def __init__(self, auto=False, mixmode=False):
        self.auto = auto
        self.mixmode = mixmode

    def wlist(self, words, nwords=50):
        """Create a list of words and clues."""
        wordlist = [line.strip().split(' ', 1) for line in words if line.strip()]
        if len(wordlist) > nwords:
            wordlist = random.sample(wordlist, nwords)
        self.wordlist = [[ComplexString(line[0].upper()), line[-1]] for line in wordlist]
        self.wordlist.sort(key=lambda i: len(i[0]), reverse=True)
        if self.mixmode:
            for line in self.wordlist:
                line[1] = self.word_mixer(line[0].lower())

    def word_mixer(self, word):
        """Create anagrams for the clues."""
        word = orig_word = list(word)
        for i in range(3):
            random.shuffle(word)
            if word != orig_word:
                break
        return ''.join(word)

    def grid_size(self, gtkmode=False):
        """Calculate the default grid size."""
        if len(self.wordlist) <= 20:
            self.nrow = self.ncol = 17
        elif len(self.wordlist) <= 100:
            self.nrow = self.ncol = int((round((len(self.wordlist) - 20) / 8.0) * 2) + 19)
        else:
            self.nrow = self.ncol = 41
        if min(self.nrow, self.ncol) <= len(self.wordlist[0][0]):
            self.nrow = self.ncol = len(self.wordlist[0][0]) + 2
        if not gtkmode and not self.auto:
            gsize = str(self.nrow) + ', ' + str(self.ncol)
            grid_size = input('Enter grid size (' + gsize + ' is the default): ')
            if grid_size:
                self.check_grid_size(grid_size)

    def check_grid_size(self, grid_size):
        try:
            nrow, ncol = int(grid_size.split(',')[0]), int(grid_size.split(',')[1])
        except:
            pass
        else:
            if len(self.wordlist[0][0]) < min(nrow, ncol):
                self.nrow, self.ncol = nrow, ncol

    def gengrid(self, name, saveformat):
        i = 0
        while 1:
            print('Calculating your crossword...')
            calc = Crossword(self.nrow, self.ncol, '-', self.wordlist)
            print(calc.compute_crossword())
            if self.auto:
                if float(len(calc.best_wordlist))/len(self.wordlist) < 0.9 and i < 5:
                    self.nrow += 2; self.ncol += 2
                    i += 1
                else:
                    break
            else:
                h = input('Are you happy with this solution? [Y/n] ')
                if h.strip() != 'n':
                    break
                inc_gsize = input('And increase the grid size? [Y/n] ')
                if inc_gsize.strip() != 'n':
                    self.nrow += 2;self.ncol += 2
        lang = 'Across/Down'.split('/')
        
        print(f"Result Grid has {self.nrow} rows and {self.ncol} cols with the best grid= {self.best_grid}, for word={calc.best_wordlist}")
        

class Crossword(object):
    def __init__(self, rows, cols, empty=' ', available_words=[]):
        self.rows = rows
        self.cols = cols
        self.empty = empty
        self.available_words = available_words
        self.let_coords = defaultdict(list)

    def prep_grid_words(self):
        self.current_wordlist = []
        self.let_coords.clear()
        self.grid = [[self.empty]*self.cols for i in range(self.rows)]
        self.available_words = [word[:2] for word in self.available_words]
        self.first_word(self.available_words[0])

    def compute_crossword(self, time_permitted=1.00):
        self.best_wordlist = []
        wordlist_length = len(self.available_words)
        time_permitted = float(time_permitted)
        start_full = float(time.time())
        while (float(time.time()) - start_full) < time_permitted:
            self.prep_grid_words()
            [self.add_words(word) for i in range(2) for word in self.available_words
             if word not in self.current_wordlist]
            if len(self.current_wordlist) > len(self.best_wordlist):
                self.best_wordlist = list(self.current_wordlist)
                self.best_grid = list(self.grid)
            if len(self.best_wordlist) == wordlist_length:
                break
        #answer = '\n'.join([''.join(['{} '.format(c) for c in self.best_grid[r]]) for r in range(self.rows)])
        answer = '\n'.join([''.join([u'{} '.format(c) for c in self.best_grid[r]])
                            for r in range(self.rows)])
        return answer + '\n\n' + str(len(self.best_wordlist)) + ' out of ' + str(wordlist_length)

    def get_coords(self, word):
        """Return possible coordinates for each letter."""
        word_length = len(word[0])
        coordlist = []
        temp_list =  [(l, v) for l, letter in enumerate(word[0])
                      for k, v in self.let_coords.items() if k == letter]
        for coord in temp_list:
            letc = coord[0]
            for item in coord[1]:
                (rowc, colc, vertc) = item
                if vertc:
                    if colc - letc >= 0 and (colc - letc) + word_length <= self.cols:
                        row, col = (rowc, colc - letc)
                        score = self.check_score_horiz(word, row, col, word_length)
                        if score:
                            coordlist.append([rowc, colc - letc, 0, score])
                else:
                    if rowc - letc >= 0 and (rowc - letc) + word_length <= self.rows:
                        row, col = (rowc - letc, colc)
                        score = self.check_score_vert(word, row, col, word_length)
                        if score:
                            coordlist.append([rowc - letc, colc, 1, score])
        if coordlist:
            return max(coordlist, key=itemgetter(3))
        else:
            return

    def first_word(self, word):
        """Place the first word at a random position in the grid."""
        vertical = random.randrange(0, 2)
        if vertical:
            row = random.randrange(0, self.rows - len(word[0]))
            col = random.randrange(0, self.cols)
        else:
            row = random.randrange(0, self.rows)
            col = random.randrange(0, self.cols - len(word[0]))
        self.set_word(word, row, col, vertical)

    def add_words(self, word):
        """Add the rest of the words to the grid."""
        coordlist = self.get_coords(word)
        if not coordlist:
            return
        row, col, vertical = coordlist[0], coordlist[1], coordlist[2]
        self.set_word(word, row, col, vertical)

    def check_score_horiz(self, word, row, col, word_length, score=1):
        cell_occupied = self.cell_occupied
        if col and cell_occupied(row, col-1) or col + word_length != self.cols and cell_occupied(row, col + word_length):
            return 0
        for letter in word[0]:
            active_cell = self.grid[row][col]
            if active_cell == self.empty:
                if row + 1 != self.rows and cell_occupied(row+1, col) or row and cell_occupied(row-1, col):
                    return 0
            elif active_cell == letter:
                score += 1
            else:
                return 0
            col += 1
        return score

    def check_score_vert(self, word, row, col, word_length, score=1):
        cell_occupied = self.cell_occupied
        if row and cell_occupied(row-1, col) or row + word_length != self.rows and cell_occupied(row + word_length, col):
            return 0
        for letter in word[0]:
            active_cell = self.grid[row][col]
            if active_cell == self.empty:
                if col + 1 != self.cols and cell_occupied(row, col+1) or col and cell_occupied(row, col-1):
                    return 0
            elif active_cell == letter:
                score += 1
            else:
                return 0
            row += 1
        return score

    def set_word(self, word, row, col, vertical):
        """Put words on the grid and add them to the word list."""
        word.extend([row, col, vertical])
        self.current_wordlist.append(word)

        horizontal = not vertical
        for letter in word[0]:
            self.grid[row][col] = letter
            if (row, col, horizontal) not in self.let_coords[letter]:
                self.let_coords[letter].append((row, col, vertical))
            else:
                self.let_coords[letter].remove((row, col, horizontal))
            if vertical:
                row += 1
            else:
                col += 1

    def cell_occupied(self, row, col):
        cell = self.grid[row][col]
        if cell == self.empty:
            return False
        else:
            return True


usage_info = """The word list file contains the words and clues, or just words, that you want in your crossword.
For further information on how to format the word list file and about the other options, please consult the man page.
"""

def main():
    parser = argparse.ArgumentParser(description='Crossword generator.', prog='genxword', epilog=usage_info)
    # parser.add_argument('infile', help='Name of word list file.', default='./2000_comwords_ENG.txt')
    # parser.add_argument('saveformat', help='Save files as A4 pdf (p), letter size pdf (l), png (n), svg(s) and/or ipuz(z).', default='n')
    parser.add_argument('-a', '--auto', dest='auto', action='store_true', help='Automated (non-interactive) option.')
    parser.add_argument('-n', '--number', dest='nwords', type=int, default=50, help='Number of words to be used.')
    parser.add_argument('-o', '--output', dest='output', default='Gumby', help='Name of crossword.')
    args = parser.parse_args()
    gen = Genxword(args.auto)
    infile = './2000_comwords_ENG.txt'
    with open(infile) as i:
        gen.wlist(i, args.nwords)
    gen.grid_size()
    gen.gengrid(args.output, 'n')


if __name__ == '__main__':
    main()

