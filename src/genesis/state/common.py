from dataclasses import dataclass, field
from typing import List, Dict


def list_field_with_default(default: any):
    field(default_factory=lambda: [default])


class OwnAttrsMixin:
    def attrs(self) -> List[str]:
        """
        Returns list of attributes which do not start with "_"
        """

        return [v for v in self.__dict__.keys() if not v.startswith("_")]


class ListConstructorMixin:
    @classmethod
    def from_dict_list(cls, list_: List[Dict]):
        return [cls(**v) for v in list_]


@dataclass
class Coin(ListConstructorMixin, OwnAttrsMixin):
    amount: str
    denom: str
