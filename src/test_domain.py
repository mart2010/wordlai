import pytest
import domain


def tst_count_chars():
    try:
        ret = domain.count_chars('-------')
        assert False, "Expected ValueError for no letters"
    except ValueError:
        pass
    
    ret = domain.count_chars('--R----G--E')
    assert ret == (3, 2, 10)

    ret = domain.count_chars('F-ß---K---中--')
    assert ret == (4, 0, 10)



def tst_get_regex():
    # en empty grid not valid (for 1st word is handled exceptionnally) 
    try:
        ret = domain.get_regex('-------')
        assert False, "Expected ValueError for no letters"
    except ValueError:
        pass

    ret = domain.get_regex('--R----G--E')
    assert ret == r'\[(\d+)\](\w{0,2}R\w{4}G\w{2}E)\[(\d+)\]'

    ret = domain.get_regex('F-ß---K---中--')
    assert ret == r'\[(\d+)\](F\w{1}ß\w{3}K\w{3}中\w{0,2})\[(\d+)\]'


def tst_gen_patterns():

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


def tst_word():
    word = domain.Word(word='Test')
    word.set_position(row=1, col=2, direction=0)
    assert word.letter_at(0,0) is None
    assert word.letter_at(1,1) is None
    assert word.letter_at(1,6) is None
    assert word.letter_at(1,2) == 'T'
    assert word.letter_at(1,3) == 'E'
    assert word.letter_at(1,5) == 'T'
    assert word.canonical == 'TEST'
    assert word.blocked_span(padding=False) == (2,5)
    assert word.blocked_span_list() == [2,3,4,5]
    assert word.blocked_span(padding=True) == (1,6)

    word.set_position(row=0, col=0, direction=1)
    assert word.letter_at(0,0) == 'T'
    assert word.letter_at(3,0) == 'T'
    assert word.letter_at(4,0) is None
    assert word.blocked_span(padding=False) == (0,3)
    assert word.blocked_span_list() == [0,1,2,3]
    assert word.blocked_span(padding=True) == (0,4)

def ppuzzle(title, puzzle):
    print('\n' + title + ':') 
    print(puzzle)


def test_puzzle():
    puzzle = domain.Puzzle(grid_size=9, available_words=[('Word', ''), ('WTester', ''),
                                                          ('Bada', ''), ('Ecolo',''),
                                                          ('Sm',''), ('Tooooolonnnnnnnggg', '')])
    assert puzzle.min_size_word == 2
    assert puzzle.available_wordseq == '[0]WTESTER[1]ECOLO[2]WORD[3]BADA[4]SM'
    
    ppuzzle('Initial empty', puzzle)

    try:
        puzzle._get_fullpattern(direction=1, index=2)
        assert False
    except Exception:
        pass

    #######################################################################
    # add a word directy (not testing yet add_word()
    title = 'One word'
    word = domain.Word('word', start_row=2, start_col=3, direction=1)
    puzzle.placed_words.setdefault(word.direction, {}).setdefault(word.start_col, []).append(word)
    ppuzzle(title, puzzle)

    assert puzzle._get_fullpattern(word.direction, word.start_col) == '-000000--'
    assert puzzle.get_letter_sequences(word.direction, word.start_col) == []

    assert puzzle._get_fullpattern(word.direction, word.start_col-1) == '--0000---'
    assert puzzle.get_letter_sequences(word.direction, word.start_col-1) == []

    assert puzzle._get_fullpattern(word.direction, word.start_col+1) == '--0000---'
    assert puzzle.get_letter_sequences(word.direction, word.start_col+1) == []

    assert puzzle._get_fullpattern(1-word.direction,word.start_row) == '---W-----'
    assert puzzle.get_letter_sequences(1-word.direction, word.start_row) == [('---W-----',0)]

    assert puzzle._get_fullpattern(1-word.direction,5) == '---D-----'
    assert puzzle.get_letter_sequences(1-word.direction, 5) == [('---D-----',0)]

    try:
        puzzle._get_fullpattern(word.direction, 8)
        assert False
    except Exception:
        pass

    #######################################################################
    title = 'Two with Bada'
    bada = domain.Word('bada', start_row=5, start_col=1, direction=0)
    puzzle.placed_words.setdefault(bada.direction, {}).setdefault(bada.start_row, []).append(bada)
    ppuzzle(title, puzzle)

    assert puzzle._get_fullpattern(bada.direction, bada.start_row) == '000000---'
    assert puzzle._get_fullpattern(bada.direction, bada.start_row-1) == '-00R0----'
    assert puzzle._get_fullpattern(bada.direction, bada.start_row-2) == '---O-----'
    assert puzzle.get_letter_sequences(bada.direction, bada.start_row-2) == [('---O-----',0)]

    assert puzzle._get_fullpattern(bada.direction, bada.start_row+1) == '-0000----'
    assert puzzle.get_letter_sequences(bada.direction, bada.start_row+1) == []


    assert puzzle._get_fullpattern(1-bada.direction, 1) == '-----B---'
    assert puzzle._get_fullpattern(1-bada.direction, 4) == '--000A---'
    assert puzzle.get_letter_sequences(1-bada.direction, 4) == [('A---',5)]


    #######################################################################
    title = 'Three with ecolo'
    ecolo = domain.Word('ecolo', start_row=3, start_col=1, direction=0)
    puzzle.placed_words.setdefault(ecolo.direction, {}).setdefault(ecolo.start_row, []).append(ecolo)
    ppuzzle(title, puzzle)

    assert puzzle._get_fullpattern(1, 1) == '---E-B---'
    assert puzzle.get_letter_sequences(1, 1) == [('---E-B---',0)]
    assert puzzle._get_fullpattern(1, 2) == '--0C0A---'
    assert puzzle.get_letter_sequences(1, 2) == [('A---',5)]

    assert puzzle._get_fullpattern(1, 5) == '---O-----'
    #assert puzzle.get_letter_sequences(1, 5) == [('---E-B---',0)]
