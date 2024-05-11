import time
from pprint import pprint

import pytest

import wiretap
from wiretap.counter import Counter


def test_counter():
    c = Counter()
    assert c.elapsed() == 0
    assert len(c.items) == 0
    assert c.min() is None
    assert c.max() is None
    assert c.avg() == 0

    with c.measure("foo"):
        time.sleep(3)

    with c.measure("bar"):
        time.sleep(2)

    with c.measure("baz"):
        time.sleep(1)

    with c.measure("qux"):
        time.sleep(4)

    assert len(c.items) == 4
    assert round(c.min().elapsed, 1) == 1
    assert round(c.max().elapsed, 1) == 4
    assert round(c.avg(), 1) == 2.5

    pprint(c.dump())
