from dataclasses import dataclass
from typing import List, Dict

from src.genesis.state.common import Coin


@dataclass(frozen=True)
class DepositParams:
    max_deposit_period: str  # e.g. "1209600s"
    min_deposit: List[Coin]


@dataclass(frozen=True)
class ProposalChanges:
    key: str
    subspace: str
    value: str


@dataclass(frozen=True)
class ProposalContent:
    # TODO: `@type` in JSON
    type: str
    changes: List[ProposalChanges]


@dataclass(frozen=True)
class FinalTallyResult:
    abstain: str  # int
    no: str  # int
    no_with_veto: str  # int
    yes: str  # int


@dataclass(frozen=True)
class Proposal:
    content: ProposalContent
    deposit_end_time: str  # e.g. "2021-12-27T19:50:58.094611598Z"
    final_tally_result: FinalTallyResult
    proposal_id: str  # int
    status: str  # enum e.g. PROPOSAL_STATUS_PASSED
    submit_time: str  # e.g. "2021-12-27T19:50:58.094611598Z"
    total_deposit: List[Coin]
    voting_end_time: str  # e.g. "2021-12-27T19:50:58.094611598Z"
    voting_start_time: str  # e.g. "2021-12-27T19:50:58.094611598Z"


@dataclass(frozen=True)
class TallyParams:
    quorum: str  # float
    threshold: str  # float
    veto_threshold: str  # float


@dataclass(frozen=True)
class VotingParams:
    voting_period: str  # e.g. "1209600s"


@dataclass(frozen=True)
class GovState:
    deposit_params: DepositParams
    deposits: List[Dict]
    proposals: List[Proposal]
    starting_proposal_id: str  # int
    tally_params: TallyParams
    votes: List[Dict]
    voting_params: VotingParams
