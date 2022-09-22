# construct Observers
from typing import Tuple

from reactivex import operators

from src.genesis.genesis import GenesisSingleton

balances_key_paths = ".data.app_state.bank.balances"


def filter_balances(next_: Tuple[str, any]):
    key, _ = next_
    return key.startswith(balances_key_paths)


GenesisSingleton().source.pipe(
    operators.filter(filter_balances)
)
