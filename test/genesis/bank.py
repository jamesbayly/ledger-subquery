import sys
import unittest

sys.path.insert(0, "/home/bwhite/Projects/fetch.ai/ledger-subquery")

from src.genesis.state.bank import BankState


class TestBank(unittest.TestCase):
    def test_constructor(self):

        data = {
            "balances": [
                {"address": "addr123", "coins": [
                    {"amount": "123", "denom": "a_tokens"},
                    {"amount": "456", "denom": "b_tokens"},
                ]},
            ],
            "supply": [
                {"amount": "987", "denom": "a_tokens"},
                {"amount": "654", "denom": "b_tokens"},
            ]
        }

        bank_state = BankState(**data)

        for i, balance in enumerate(bank_state.balances):
            self.assertEqual(balance.address, data["balances"][i]["address"])

            for j, coin in enumerate(balance.coins):
                expected_coin = data["balances"][i]["coins"][j]
                self.assertEqual(coin.amount, expected_coin["amount"])
                self.assertEqual(coin.denom, expected_coin["denom"])

        for i, coin in enumerate(bank_state.supply):
            expected_coin = data["supply"][i]
            self.assertEqual(coin.amount, expected_coin["amount"])
            self.assertEqual(coin.denom, expected_coin["denom"])


if __name__ == '__main__':
    unittest.main()
