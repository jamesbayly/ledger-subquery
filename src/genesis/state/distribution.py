from dataclasses import dataclass
from typing import List, Dict

from src.genesis.state.common import Coin, ListConstructorMixin


@dataclass(frozen=True)
class StartingInfo:
    height: str
    previous_period: str
    stake: str  # float; e.g. "7088940.000000000000000000"


@dataclass(frozen=True)
class DelegatorStartingInfo:
    delegator_address: str
    starting_info: StartingInfo
    validator_address: str

    @classmethod
    # TODO: return type not defined yet? `-> List[DelegatorStartingInfo]`
    def from_dict_list(cls, infos: List[Dict]):

        return [cls(**i) for i in infos]


@dataclass(frozen=True)
class OutstandingReward:
    outstanding_rewards: List[Coin]
    validator_address: str


@dataclass(frozen=True)
class DistParams:
    base_proposer_reward: str  # float
    bonus_proposer_reward: str  # float
    community_tax: str  # float
    withdraw_addr_enabled: bool


@dataclass(frozen=True)
class AccumulatedCommission:
    commission: List[Coin]


@dataclass(frozen=True)
class ValidatorAccumulatedCommission(ListConstructorMixin):
    accumulated: AccumulatedCommission
    validator_address: str


@dataclass(frozen=True)
class CurrentRewards:
    period: str  # int
    rewards: List[Coin]


@dataclass(frozen=True)
class ValidatorCurrentReward(ListConstructorMixin):
    rewards: CurrentRewards
    validator_address: str


@dataclass(frozen=True)
class HistoricalRewards:
    cumulative_reward_ratio: List[Coin]
    reference_count: int


@dataclass(frozen=True)
class ValidatorHistoricalReward(ListConstructorMixin):
    period: str
    rewards: HistoricalRewards


@dataclass(frozen=True)
class SlashEvent:
    fraction: str  # float
    validator_period: str  # int


@dataclass(frozen=True)
class ValidatorSlashEvent(ListConstructorMixin):
    height: str  # int
    period: str  # int
    validator_address: str
    validator_slash_event: SlashEvent


@dataclass(frozen=True)
class DistState:
    delegator_starting_infos: List[DelegatorStartingInfo]
    delegator_withdraw_infos: List[Dict]
    fee_pool: Dict[str, List[Coin]]
    outstanding_rewards: OutstandingReward
    params: DistParams
    previous_proposer: str
    validator_accumulated_commissions: List[ValidatorAccumulatedCommission]
    validator_current_rewards: List[ValidatorCurrentReward]
    validator_historical_rewards: List[ValidatorHistoricalReward]
    validator_slash_events: List[ValidatorSlashEvent]

    def __init__(self, **kwargs: Dict[str, any]):
        concrete_args = {
            "delegator_starting_infos": DelegatorStartingInfo.from_dict_list(kwargs["delegator_starting_infos"]),
            "validatorAccumulatedCommission": ValidatorAccumulatedCommission.from_dict_list(
                kwargs["validator_accumulated_commission"]),
            "validatorCurrentReward": ValidatorCurrentReward.from_dict_list(kwargs["validator_current_rewards"]),
            "validator_historical_rewards": ValidatorHistoricalReward.from_dict_list(
                kwargs["validator_historical_rewards"]),
            "validator_slash_events": ValidatorSlashEvent.from_dict_list(kwargs["validator_slash_events"]),
        }

        super().__init__(**{**kwargs, **concrete_args})
