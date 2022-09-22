import unittest
from typing import Optional

import reactivex as rx
from reactivex import Observer, Observable
from reactivex.disposable import Disposable
from reactivex.scheduler.scheduler import Scheduler


class Source:
    _source: Observable = None

    def __init__(self):
        self._source = rx.create(self.factory)

    def factory(self, observer, scheduler):
        observer.on_next("one")
        observer.on_next("two")
        observer.on_completed()

    def subscribe(self, *args, **kwargs):
        self._source.subscribe(*args, **kwargs)


class TestObserver(unittest.TestCase):
    def test_observer(self):
        self._value_count: int = 0
        self._last_value: any = None
        self._completed: bool = False

        def on_next(value):
            self._value_count += 1
            self._last_value = value

        def on_completed():
            self._completed = True

        source = Source()
        source.subscribe(
            on_next=on_next,
            on_completed=on_completed,
        )

        self.assertEqual(self._completed, True)
        self.assertEqual(self._value_count, 2)
        self.assertEqual(self._last_value, "two")


if __name__ == "__main__":
    unittest.main()
