from dataclasses import dataclass, field
from typing import List, Dict, Union, Optional

from reactivex import Observable, Observer, operators as op, create
from reactivex.scheduler.scheduler import Scheduler

from src.genesis.cli.download import download_json
from src.genesis.state.bank import BankState
from src.genesis.state.common import OwnAttrsMixin, list_field_with_default
from src.genesis.state.distribution import DistState
from src.genesis.state.gov import GovState


@dataclass
class PubKey:
    type: str
    value: str


@dataclass
class ValidatorData:
    address: str
    name: str
    power: str
    pub_key: PubKey


class Validator(ValidatorData):
    def __init__(self, **kwargs):
        kwargs["pub_key"] = PubKey(**kwargs["pub_key"])
        super().__init__(**kwargs)


@dataclass
class AppStateData:
    auth: Dict = field(default_factory=dict)
    # auth: AuthState = field(default_factory=AuthState)
    authz: Dict = field(default_factory=dict)
    # authz: AuthzState = field(default_factory=AuthzState)
    bank: BankState = field(default_factory=BankState)
    capability: Dict = field(default_factory=dict)
    crisis: Dict = field(default_factory=dict)
    distribution: Dict = field(default_factory=dict)
    # distribution: DistState = field(default_factory=str)
    evidence: Dict = field(default_factory=dict)
    feegrant: Dict = field(default_factory=dict)
    genutil: Dict = field(default_factory=dict)
    gov: Dict = field(default_factory=dict)
    # gov: GovState = field(default_factory=dict)
    ibc: Dict = field(default_factory=dict)
    # ibc: IBCState = field(default_factory=dict)
    mint: Dict = field(default_factory=dict)
    params: Dict = field(default_factory=dict)
    slashing: Dict = field(default_factory=dict)
    staking: Dict = field(default_factory=dict)
    # staking: StakingState = field(default_factory=dict)
    transfer: Dict = field(default_factory=dict)
    # transfer: TransferState = field(default_factory=dict)
    upgrade: Dict = field(default_factory=dict)
    # upgrade: UpgradeState = field(default_factory=dict)
    vesting: Dict = field(default_factory=dict)
    wasm: Dict = field(default_factory=dict)
    # wasm: WASMState = field(default_factory=WASMState)


class AppState(AppStateData):
    def __init__(self, **kwargs):
        bank_state_data = {}
        if kwargs.get("bank") is not None:
            bank_state_data = kwargs["bank"]

        concrete_state = {
            "bank": BankState(**bank_state_data),
            # "distribution": DistState(**kwargs["distribution"]),
            # "gov": GovState(**kwargs["gov"]),
        }
        super().__init__(**{**kwargs, **concrete_state})


@dataclass(frozen=True)
class GenesisData(OwnAttrsMixin):
    app_hash: str = field(default_factory=str)
    app_state: AppState = field(default_factory=AppState)
    chain_id: str = field(default_factory=str)
    consensus_params: Dict = field(default_factory=dict)
    genesis_time: str = field(default_factory=str)  # e.g. "2022-02-08T18:00:00Z"
    initial_height: str = field(default_factory=str)  # int; e.g. "5300201"
    validators: List[Validator] = list_field_with_default(Validator)


class Genesis:
    @staticmethod
    def download(json_url: str):
        return Genesis(**(download_json(json_url)))

    def __init__(self, **kwargs):
        if kwargs.get("app_state") is not None:
            app_state_data = kwargs["app_state"]

        kwargs["app_state"] = AppState(**app_state_data)

        self.data = GenesisData(**kwargs)
        self._source = create(self._observer_factory)

    def _observer_factory(self, observer: Observer, scheduler: Optional[Scheduler]):
        recurse_object(self, observer)

    @property
    def source(self):
        return self._source


def recurse_object(obj: OwnAttrsMixin, observer: Observer, keys_path=""):
    for attr in obj.attrs():
        next_keys_path = f"{keys_path}.{attr}"
        value = getattr(obj, attr)

        if isinstance(value, type(None)):
            continue

        if isinstance(value, list):
            for v in value:
                observer.on_next((next_keys_path, v))

        observer.on_next((next_keys_path, value))

        if isinstance(value, OwnAttrsMixin):
            recurse_object(value, observer, next_keys_path)


class GenesisSingleton:
    def __new__(cls, genesis_dict):
        if not hasattr(cls, "_genesis"):
            cls._genesis = Genesis(**genesis_dict)

        return cls._genesis
