import pytest
import domain


def test_count_chars():
    try:
        ret = domain.count_chars('-------')
        assert False, "Expected ValueError for no letters"
    except ValueError:
        pass
    
    ret = domain.count_chars('--R----G--E')
    assert ret == (3, 2, 10)

    ret = domain.count_chars('F-ß---K---中--')
    assert ret == (4, 0, 10)



def test_get_regex():
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


def test_gen_patterns():
    patterns = list(domain.gen_patterns('--R----G--E', pos=0))
    expected_patterns = [
        (r'\[(\d+)\](\w{0,2}R\w{4}G\w{2}E)\[(\d+)\]', 0),  # '--R----G--E'
        (r'\[(\d+)\](\w{0,2}R\w{4}G\w{0,1})\[(\d+)\]',0),  # '--R----G-'
        (r'\[(\d+)\](\w{0,2}R\w{0,3})\[(\d+)\]',0),        # '--R---'
        (r'\[(\d+)\](\w{0,3}G\w{2}E)\[(\d+)\]',4),         # '---G--E'
        (r'\[(\d+)\](\w{0,1}E)\[(\d+)\]',9),               # '-E'
        (r'\[(\d+)\](\w{0,3}G\w{0,1})\[(\d+)\]',4),        # '---G-' 
    ]
    assert set(patterns) == set(expected_patterns)


    patterns = list(domain.gen_patterns('F-ß---K---中--', pos=0))
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

    patterns = list(domain.gen_patterns('--中--', pos=0))
    expected_patterns = [
        (r'\[(\d+)\](\w{0,2}中\w{0,2})\[(\d+)\]', 0),            # '--中--'
    ]
    assert set(patterns) == set(expected_patterns)
