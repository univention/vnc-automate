# coding: utf-8
from __future__ import absolute_import

import pytest

from vncautomate.ocr import OCRAlgorithm, _OCRWord


@pytest.fixture
def algo():
    algo = OCRAlgorithm()
    return algo


@pytest.mark.parametrize(
    "all_words,pattern,score,match",
    [
        (["a b"], "a b c", 0.7, "a b"),
        (["a b c"], "a b c", 1.0, "a b c"),
        (["a b c d"], "a b c", 0.975, "a b c"),
        (["a b", "a b c", "a b c d"], "a b c", 1.0, "a b c"),
    ],
)
def test_find_best_matching_words(algo, all_words, pattern, score, match):
    _all_words = [[_OCRWord(word, None) for word in line.split()] for line in all_words]
    _score, _match = algo.find_best_matching_words(_all_words, pattern)
    assert (_score, " ".join(word.word for word in _match or [])) == (pytest.approx(score), match)
