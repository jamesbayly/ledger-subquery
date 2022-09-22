from typing import Dict, List

test_bank_state_balances = [{
    "address": "addr123",
    "coins": [
        {"amount": "123", "denom": "a-token"},
        {"amount": "456", "denom": "b-token"},
    ]
}]

test_bank_state_supply: List[Dict] = [
    {"amount": "987", "denom": "a-token"},
    {"amount": "654", "denom": "b-token"},
]

test_bank_state = {
    "balances": test_bank_state_balances,
    "supply": test_bank_state_supply,
}

test_app_state = {
    "bank": test_bank_state,
}

test_genesis_data = {
    "app_state": test_app_state,
    "chain_id": "test",
}
