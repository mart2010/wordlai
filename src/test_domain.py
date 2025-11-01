import pytest
import domain


def test_count_letters():
    try:
        ret = domain.count_letters('-------')
        assert False, "Expected ValueError for no letters"
    except ValueError:
        pass
    
    ret = domain.count_letters('--R----G--E')
    assert ret == (3, 2, 10)

    ret = domain.count_letters('F-ß---K---中--')
    assert ret == (4, 0, 10)



def test_get_regex():
    # en empty grid not valid (for 1st word is handled exceptionnally) 
    try:
        ret = domain.get_regex('-------', empty_marker='-')
        assert False, "Expected ValueError for no letters"
    except ValueError:
        pass

    ret = domain.get_regex('--R----G--E', empty_marker='-')
    assert ret == r'\[(\d+)\](\w{0,2}R\w{4}G\w{2}E)\[(\d+)\]'

    ret = domain.get_regex('F-ß---K---中--', empty_marker='-')
    assert ret == r'\[(\d+)\](F\w{1}ß\w{3}K\w{3}中\w{0,2})\[(\d+)\]'


def test_gen_patterns():

    try:
        for p in domain.gen_patterns('------', 0, 2):
            pass
        assert False, "Expected ValueError for no letter"
    except ValueError:
        pass

    patterns = list(domain.gen_patterns('--R----G--E', pos=0, min_size=2))
    expected_patterns = [
        (r'\[(\d+)\](\w{0,2}R\w{4}G\w{2}E)\[(\d+)\]', 0),  # '--R----G--E'
        (r'\[(\d+)\](\w{0,2}R\w{4}G\w{0,1})\[(\d+)\]',0),  # '--R----G-'
        (r'\[(\d+)\](\w{0,2}R\w{0,3})\[(\d+)\]',0),        # '--R---'
        (r'\[(\d+)\](\w{0,3}G\w{2}E)\[(\d+)\]',4),         # '---G--E'
        (r'\[(\d+)\](\w{0,1}E)\[(\d+)\]',9),               # '-E'
        (r'\[(\d+)\](\w{0,3}G\w{0,1})\[(\d+)\]',4),        # '---G-' 
    ]
    assert set(patterns) == set(expected_patterns)

    patterns = list(domain.gen_patterns('--R----G--E', pos=0, min_size=8))
    expected_patterns = [
        (r'\[(\d+)\](\w{0,2}R\w{4}G\w{2}E)\[(\d+)\]', 0),  # '--R----G--E'
        (r'\[(\d+)\](\w{0,2}R\w{4}G\w{0,1})\[(\d+)\]',0),  # '--R----G-'
    ]
    assert set(patterns) == set(expected_patterns)


    patterns = list(domain.gen_patterns('F-ß---K---中--', pos=0, min_size=3))
    expected_patterns = [
        (r'\[(\d+)\](F\w{1}ß\w{3}K\w{3}中\w{0,2})\[(\d+)\]', 0), # 'F-ß---K---中--'
        (r'\[(\d+)\](F\w{1}ß\w{3}K\w{0,2})\[(\d+)\]', 0),        # 'F-ß---K--'
        (r'\[(\d+)\](F\w{1}ß\w{0,2})\[(\d+)\]', 0),              # 'F-ß--'
        (r'\[(\d+)\](ß\w{3}K\w{3}中\w{0,2})\[(\d+)\]', 2),       # 'ß---K---中--'
        (r'\[(\d+)\](\w{0,2}K\w{3}中\w{0,2})\[(\d+)\]', 4),      # '--K---中--'
        (r'\[(\d+)\](ß\w{3}K\w{0,2})\[(\d+)\]', 2),              # 'ß---K--'
        (r'\[(\d+)\](ß\w{3}K\w{0,2})\[(\d+)\]', 2),              # 'ß---K--'
        (r'\[(\d+)\](\w{0,2}K\w{0,2})\[(\d+)\]', 4),             # '--K--'
        (r'\[(\d+)\](\w{0,2}中\w{0,2})\[(\d+)\]', 8),            # '--中--'
        (r'\[(\d+)\](ß\w{0,2})\[(\d+)\]', 2),                    # 'ß--'
    ]
    assert set(patterns) == set(expected_patterns)

    patterns = list(domain.gen_patterns('--中--', pos=0, min_size=5))
    expected_patterns = [
        (r'\[(\d+)\](\w{0,2}中\w{0,2})\[(\d+)\]', 0),            # '--中--'
    ]
    assert set(patterns) == set(expected_patterns)


def test_word():
    word = domain.Word(word='Test')
    assert word.canonical == 'TEST'
    
    loc = domain.Location(direction=0, index=1)
    word.set_position(location=loc, pos=2)
    assert word.letter_at(0,0) is None
    assert word.letter_at(1,1) is None
    assert word.letter_at(1,6) is None
    assert word.letter_at(1,2) == 'T'
    assert word.letter_at(1,3) == 'E'
    assert word.letter_at(1,5) == 'T'
    
    assert word.span(padding=False) == [2,3,4,5]
    assert word.span(padding=True) == [1,2,3,4,5,6]

    loc = domain.Location(direction=1, index=0)
    word.set_position(location=loc, pos=0)
    assert word.letter_at(0,0) == 'T'
    assert word.letter_at(3,0) == 'T'
    assert word.letter_at(4,0) is None
    assert word.span(padding=False) == [0,1,2,3]
    assert word.span(padding=True) == [0,1,2,3,4]




def tst_puzzle():
    def ppuzzle(title, puzzle):
        print('\n' + title + ':') 
        print(puzzle)

    a_words = [('Word', ''), ('Wtesber', ''), ('Sorsdela', ''),
               ('Bada', ''), ('Ecolos',''), (  'MotsdesFa',''),
               ('small', ''), ('Datavault',''), ('Short',''), 
               ('Sm',''), ('Tooooolonnnnnnnggg', ''),
            ]

    puzzle = domain.Puzzle(grid_size=9, words=a_words)
                                                          
    def word_idx(w):
        the_w = domain.Word(word=w)
        return puzzle.available_words.index(the_w)

    assert puzzle.min_size_word == 2
    assert puzzle.available_wordseq == '[0]MOTSDESFA[1]DATAVAULT[2]SORSDELA[3]WTESBER[4]ECOLOS[5]SMALL[6]SHORT[7]WORD[8]BADA[9]SM'
    assert len(puzzle.available_words) == len(a_words) - 1
    
    ppuzzle('Initial', puzzle)

    try:
        puzzle._get_entirepattern(direction=1, index=2)
        assert False
    except Exception:
        pass

    #######################################################################
    title = 'One word'

    word = puzzle.place_word(word_idx('Word'), row=2, col=3, direction=1)
    assert word.canonical == 'WORD'
    assert word.row == 2
    assert word.col == 3
    assert word.direction == 1

    ppuzzle(title, puzzle)
    assert puzzle.placed_words[word.direction][word.col][0] == word
    assert puzzle.empty_indexes.get(1-word.direction) == [i for i in range(9) if i not in word.span()]
    assert puzzle.available_wordseq == '[0]MOTSDESFA[1]DATAVAULT[2]SORSDELA[3]WTESBER[4]ECOLOS[5]SMALL[6]SHORT[8]BADA[9]SM'

    assert puzzle._get_entirepattern(word.direction, word.col) == '-000000--'
    assert puzzle._get_subpatterns(word.direction, word.col) == -3

    try: 
        puzzle._get_entirepattern(word.direction, word.col-1)
        assert False
    except Exception:
        pass

    assert puzzle._get_entirepattern(1-word.direction,word.row) == '---W-----'
    assert puzzle._get_subpatterns(1-word.direction, word.row) == [('---W-----',0)]

    assert puzzle._get_entirepattern(1-word.direction,5) == '---D-----'
    assert puzzle._get_subpatterns(1-word.direction, 5) == [('---D-----',0)]

    #######################################################################
    title = 'Two with Bada'
    
    bada = puzzle.place_word(word_idx('Bada'), row=5, col=1, direction=0)
    ppuzzle(title, puzzle)
    
    assert puzzle.placed_words[bada.direction][bada.row][0] == bada
    assert puzzle.empty_indexes.get(1-bada.direction) == [i for i in range(9) if i not in bada.span()]
    assert puzzle.available_wordseq == '[0]MOTSDESFA[1]DATAVAULT[2]SORSDELA[3]WTESBER[4]ECOLOS[5]SMALL[6]SHORT[9]SM'
    
    assert puzzle._get_entirepattern(bada.direction, bada.row) == '000000---'
    assert puzzle._get_entirepattern(bada.direction, bada.row-1) == '-00R0----'
    assert puzzle._get_entirepattern(bada.direction, bada.row-2) == '---O-----'
    assert puzzle._get_subpatterns(bada.direction, bada.row-2) == [('---O-----',0)]

    assert puzzle._get_entirepattern(1-bada.direction, 1) == '-----B---'
    assert puzzle._get_entirepattern(1-bada.direction, 4) == '--000A---'
    assert puzzle._get_subpatterns(1-bada.direction, 4) == [('A---',5)]


    #######################################################################
    title = 'Three with ecolos'

    ecolos = puzzle.place_word(word_idx('Ecolos'), row=3, col=1, direction=0)
    ppuzzle(title, puzzle)

    assert puzzle.available_wordseq == '[0]MOTSDESFA[1]DATAVAULT[2]SORSDELA[3]WTESBER[5]SMALL[6]SHORT[9]SM'

    assert puzzle._get_entirepattern(1, 1) == '---E-B---'
    assert puzzle._get_subpatterns(1, 1) == [('---E-B---',0)]
    assert puzzle._get_entirepattern(1, 2) == '--0C0A---'
    assert puzzle._get_subpatterns(1, 2) == [('A---',5)]

    assert puzzle._get_entirepattern(1, 5) == '---O-0---'
    assert puzzle._get_subpatterns(1, 5) == [('---O-',0)]

    assert puzzle._get_entirepattern(0, 4) == '-00R000--'
    assert puzzle._get_subpatterns(0, 4) == []


    #######################################################################
    title = 'Four with Sorsdela'

    ecolos = puzzle.place_word(word_idx('Sorsdela'), row=0, col=6, direction=1)
    ppuzzle(title, puzzle)

    assert puzzle.available_wordseq == '[0]MOTSDESFA[1]DATAVAULT[3]WTESBER[5]SMALL[6]SHORT[9]SM'

    assert puzzle._get_entirepattern(1, 6) == '000000000'
    assert puzzle._get_subpatterns(1, 6) == -1

    assert puzzle._get_entirepattern(0, 4) == '-00R00D--'
    assert puzzle._get_subpatterns(0, 4) == [('D--',6)]

    assert puzzle._get_entirepattern(0, 7) == '------A--'
    assert puzzle._get_subpatterns(0, 7) == [('------A--',0)]

    # there is one letter + empty cell, so no exception/condition (could accomodate smallest word)!
    assert puzzle._get_entirepattern(1, 5) == '000O0000-'
    assert puzzle._get_subpatterns(1, 5) == []

    assert puzzle._get_entirepattern(0,2) == '-00W00R--'
    assert puzzle._get_subpatterns(1-word.direction, word.row) == [('R--',6)]


    #######################################################################
    title = 'Five with Wtesber'

    ecolos = puzzle.place_word(word_idx('Wtesber'), row=1, col=1, direction=1)
    ppuzzle(title, puzzle)

    assert puzzle.available_wordseq == '[0]MOTSDESFA[1]DATAVAULT[5]SMALL[6]SHORT[9]SM'

    assert puzzle._get_entirepattern(0,7) == '-R----A--'
    assert puzzle._get_subpatterns(0,7) == [('-R----A--',0)]
