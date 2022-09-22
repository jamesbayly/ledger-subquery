import sys
import unittest
from pathlib import Path

from helpers.genesis_data import test_bank_state

repo_root_path = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(repo_root_path))

from src.genesis.state.bank import BankState


class TestBank(unittest.TestCase):
    def test_constructor(self):
        bank_state = BankState(**test_bank_state)

        for i, balance in enumerate(bank_state.balances):
            self.assertEqual(balance.address, test_bank_state["balances"][i]["address"])

            for j, coin in enumerate(balance.coins):
                expected_coin = test_bank_state["balances"][i]["coins"][j]
                self.assertEqual(coin.amount, expected_coin["amount"])
                self.assertEqual(coin.denom, expected_coin["denom"])

        for i, coin in enumerate(bank_state.supply):
            expected_coin = test_bank_state["supply"][i]
            self.assertEqual(coin.amount, expected_coin["amount"])
            self.assertEqual(coin.denom, expected_coin["denom"])


if __name__ == '__main__':
    unittest.main()
