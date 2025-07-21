import time
from pprint import pprint

import pytest

import wiretap
from wiretap.scopes import LoopScope


def test_counter():
    c = LoopScope()
    assert c.duration_ms == 0
    assert c.count == 0
    assert c.min.item_id is None
    assert c.max.item_id is None
    assert c.mean == 0

    with c.iteration("foo"):
        time.sleep(3)

    with c.iteration("bar"):
        time.sleep(2)

    with c.iteration("baz"):
        time.sleep(1)

    with c.iteration("qux"):
        time.sleep(4)

    assert c.count == 4
    assert round(c.min.duration_ms, 1) == 1
    assert round(c.max.duration_ms, 1) == 4
    assert round(c.mean, 1) == 2.5
    assert round(c.duration_ms, 1) == 10

    pprint(c.state())
