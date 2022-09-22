from dataclasses import dataclass, field
from typing import List, Dict

from src.genesis.state.common import Coin, ListConstructorMixin, list_field_with_default, OwnAttrsMixin


@dataclass(frozen=True)
class BalanceData(ListConstructorMixin):
    address: str
    coins: List[Coin]


class Balance(BalanceData, ListConstructorMixin, OwnAttrsMixin):
    def __init__(self, **kwargs):
        kwargs["coins"] = Coin.from_dict_list(kwargs["coins"])
        super().__init__(**kwargs)


@dataclass(frozen=True)
class BankStateData:
    balances: List[Balance] = list_field_with_default(Balance)
    denom_metadata: List[Dict] = list_field_with_default(dict)
    params: Dict = field(default_factory=dict)
    supply: List[Coin] = list_field_with_default(Coin)


class BankState(OwnAttrsMixin, BankStateData):
    def __init__(self, **kwargs: Dict[str, any]):
        for k in [k for k in vars(BankStateData) if not k.startswith("_")]:
            if kwargs.get(k) is None:
                kwargs[k] = ""

        kwargs["balances"] = Balance.from_dict_list(kwargs["balances"])
        kwargs["supply"] = Coin.from_dict_list(kwargs["supply"])
        super().__init__(**kwargs)
