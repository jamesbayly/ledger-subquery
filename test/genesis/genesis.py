import sys
import unittest
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from reactivex import operators

from helpers.genesis_data import test_genesis_data, test_bank_state

repo_root_path = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(repo_root_path))

from src.genesis.genesis import Genesis, GenesisData, GenesisSingleton
from src.genesis.state.bank import Balance
from src.genesis.state.common import OwnAttrsMixin


def check_attrs(test_case: unittest.TestCase, expected: any, actual: any):
    for attr in actual.attrs():
        # TODO: unworkaround
        if attr == "data":
            expected_attr = expected
        else:
            expected_attr = expected[attr]
        actual_attr = getattr(actual, attr)

        def check(expected_: any, actual_: any):
            if isinstance(actual_, OwnAttrsMixin):
                check_attrs(test_case, expected_, actual_)
                return

            test_case.assertEqual(expected_, actual_)

        def check_dict(expected_: Dict, actual_: Dict):
            for k, v in actual_.items():
                check(expected_[k], v)

        def check_list(expected_: List, actual_: List):
            for i, v in enumerate(actual_):
                check(expected_[i], v)

        if isinstance(actual_attr, dict):
            check_dict(expected_attr, actual_attr)

        elif isinstance(actual_attr, list):
            test_case.assertEqual(len(expected_attr), len(actual_attr))
            check_list(expected_attr, actual_attr)

        elif isinstance(actual_attr, OwnAttrsMixin):
            check_attrs(test_case, expected_attr, actual_attr)

        else:
            test_case.assertEqual(expected_attr, actual_attr)


class TestGenesis(unittest.TestCase):
    def test_constructor(self):
        expected_genesis = test_genesis_data
        actual_genesis = Genesis(**test_genesis_data)

        check_attrs(self, expected_genesis, actual_genesis)

    def test_source_subscribe(self):
        seen_values = {}
        complete = []
        test_key_paths = ".app_state.bank.balances"
        expected_genesis = test_genesis_data
        actual_genesis = Genesis(**test_genesis_data)

        def balances_filter(value: Tuple[str, any]) -> bool:
            key, _ = value
            return key.startswith(test_key_paths)

        def on_next(next_: Tuple[str, any]):
            key, value = next_
            print(f"key: {key} | value: {value}")
            # TODO something more python idomatic (maybe mocks)
            seen_values[key] = value

        def on_completed():
            print("complete!")
            # TODO something more python idomatic (maybe mocks)
            complete.append(0)

        actual_genesis.source.pipe(
            operators.filter(balances_filter)
        ).subscribe(on_next=on_next, on_completed=on_completed)

        self.assertEqual(1, len(complete))
        self.assertListEqual([test_key_paths], list(seen_values.keys()))
        self.assertEqual(Balance, type(seen_values[test_key_paths]))
        self.assertEqual(
            actual_genesis.data.app_state.bank.balances[0],
            seen_values[test_key_paths]
        )


# class TestGenesisSingleton(unittest.TestCase):
#     # setup class
#     #  serve static JSON (string literal)
#     # TOSO: !!!
#     # TOSO: !!!
#     # TODO: resume here
#     # TOSO: !!!
#     # TOSO: !!!
#
#     def test_memoization(self):
#         genesis = GenesisSingleton()
#
#
# if __name__ == "__main__":
#     unittest.main()
