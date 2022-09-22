import sys
import unittest
from pathlib import Path
from typing import Dict, List

repo_root_path = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(repo_root_path))

from src.genesis.genesis import Genesis, GenesisData, GenesisSingleton
from src.genesis.state.common import OwnAttrsMixin
from test.helpers.genesis_data import test_genesis_data, test_bank_state


class TestGenesis(unittest.TestCase):
    def test_constructor(self):
        expected_genesis = test_genesis_data
        actual_genesis = Genesis(**test_genesis_data)

        def check_attrs(obj: OwnAttrsMixin):
            for attr in obj.attrs():
                expected_attr_value = getattr(expected_genesis, attr)
                actual_attr_value = getattr(actual_genesis, attr)

                def check(actual: any, expected: any):
                    if isinstance(actual, OwnAttrsMixin):
                        check_attrs(actual)
                        return

                    self.assertEqual(actual, expected)

                def check_dict(actual: Dict, expected: Dict):
                    for k, v in actual.items():
                        check(v, expected[k])

                def check_list(actual: List, expected: List):
                    for i, v in enumerate(actual):
                        check(v, expected[i])

                if isinstance(expected_attr_value, dict):
                    check_dict(actual_attr_value, expected_attr_value)

                elif isinstance(expected_attr_value, list):
                    self.assertEqual(len(actual_attr_value), len(expected_attr_value))
                    check_list(actual_attr_value, expected_attr_value)

                elif isinstance(expected_attr_value, OwnAttrsMixin):
                    check_attrs(actual_attr_value)

                else:
                    self.assertEqual(actual_attr_value, expected_attr_value)

if __name__ == "__main__":
    unittest.main()
