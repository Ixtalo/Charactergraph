#!pytest
# -*- coding: utf-8 -*-
# pylint: disable=C0301,C0116
"""
Unit tests for chractergraph.py, using pytest.
"""

import types

import pytest

from charactergraph import Charactergraph


def test_segment_text():
    with pytest.raises(ValueError):
        next(Charactergraph.segment_text('foo', 0))
    with pytest.raises(ValueError):
        next(Charactergraph.segment_text('foo', -1))
    with pytest.raises(ValueError):
        # noinspection PyTypeChecker
        next(Charactergraph.segment_text('foo', 'X'))
    with pytest.raises(ValueError):
        next(Charactergraph.segment_text('foo', 3))

    ## test
    generator = Charactergraph.segment_text('999 1000 1001 1002 1003 1004', 10)
    actual = list(generator)
    ## check
    expected = ['999 1000', '1001 1002', '1003 1004']
    assert isinstance(generator, types.GeneratorType)
    assert actual == expected


def test_read_file_lines():
    with pytest.raises(ValueError):
        # noinspection PyTypeChecker
        Charactergraph.read_file_lines(None)
    with pytest.raises(ValueError):
        Charactergraph.read_file_lines('')
    with pytest.raises(ValueError):
        Charactergraph.read_file_lines('/')

    actual = Charactergraph.read_file_lines(__file__)
    assert len(actual) > 30
    assert actual[0] == '"""'
    assert actual[1] == 'Unit tests for chractergraph.py, using pytest.'
    assert actual[2] == '"""'
    for line in actual:
        assert not line.startswith('#')
        assert line.strip() != ''


def test_read_file_lines_lowercase():
    actual = Charactergraph.read_file_lines(__file__, lowercase=True)
    assert actual[1] == 'unit tests for chractergraph.py, using pytest.'


def test_replace_space_underscore_fornames():
    actual = Charactergraph.replace_space_underscore_fornames('Moby Dick, Captain Ahab',
                                                              ('Moby Dick', 'Captain Ahab'))
    expected = 'Moby_Dick, Captain_Ahab'
    assert actual == expected


def test_get_most_frequent_items_inorder():
    actual = Charactergraph.get_most_frequent_items_inorder((6, 55, 1, 55, 7, 8, 1, 9, 55), 2)
    expected = [55, 1]
    assert actual == expected

    actual = Charactergraph.get_most_frequent_items_inorder((6, 1, 1, 55, 7, 8, 9, 55, 55), 100)
    expected = [6, 1, 55, 7, 8, 9]
    assert actual == expected


def test_names_to_rulepatterns():
    actual = Charactergraph.names_to_rulepatterns([])
    expected = []
    assert actual == expected

    actual = Charactergraph.names_to_rulepatterns(['Moby Dick', 'Captain Ahab'])
    expected = [{'label': 'PERSON', 'pattern': 'Moby Dick'}, {'label': 'PERSON', 'pattern': 'Captain Ahab'}]
    assert actual == expected


def test_get_person_names():
    text = 'last night i saw a black dog barking at a kid. My Moby Dick is not a Captain. ' \
           'Hercules is great. And Araminta is my girl. New York is a location.'

    actual = Charactergraph.get_person_names(text)
    expected = ['Araminta']
    assert actual == expected

    actual = Charactergraph.get_person_names(text, ner_names=('Moby Dick',))
    expected = ['Moby_Dick', 'Araminta']
    assert actual == expected
