import os
import unittest, psycopg

import requests
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.aerial.tx import Transaction
from cosmpy.crypto.keypairs import PrivateKey
from cosmpy.crypto.address import Address
from cosmpy.protos.cosmos.gov.v1beta1 import tx_pb2 as gov_tx, gov_pb2, query_pb2 as gov_query, query_pb2_grpc
from cosmpy.protos.cosmos.base.v1beta1 import coin_pb2
from cosmpy.protos.cosmwasm.wasm.v1 import tx_pb2 as wasm_tx, query_pb2 as wasm_query
from cosmpy.aerial.contract import LedgerContract
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins
from cosmpy.aerial.client import LedgerClient, NetworkConfig, utils
from google.protobuf import any_pb2
import grpc, json


class Base(unittest.TestCase):
    delegator_wallet = None
    delegator_address = None

    validator_wallet = None
    validator_address = None
    validator_operator_address = None

    ledger_client = None
    db = None
    db_cursor = None

    @classmethod
    def setUpClass(cls):
        validator_mnemonic = "nut grocery slice visit barrel peanut tumble patch slim logic install evidence fiction shield rich brown around arrest fresh position animal butter forget cost"
        validator_seed_bytes = Bip39SeedGenerator(validator_mnemonic).Generate()
        validator_bip44_def_ctx = Bip44.FromSeed(validator_seed_bytes, Bip44Coins.COSMOS).DeriveDefaultPath()
        cls.validator_wallet = LocalWallet(PrivateKey(validator_bip44_def_ctx.PrivateKey().Raw().ToBytes()))
        cls.validator_address = str(cls.validator_wallet.address())
        cls.validator_operator_address = Address(bytes(cls.validator_wallet.address()), prefix="fetchvaloper")

        delegator_mnemonic = "dismiss domain uniform image cute buzz ride anxiety nose canvas ripple stock buffalo bitter spirit maximum tone inner couch forum equal usage state scan"
        delegator_seed_bytes = Bip39SeedGenerator(delegator_mnemonic).Generate()
        delegator_bip44_def_ctx = Bip44.FromSeed(delegator_seed_bytes, Bip44Coins.COSMOS).DeriveDefaultPath()
        cls.delegator_wallet = LocalWallet(PrivateKey(delegator_bip44_def_ctx.PrivateKey().Raw().ToBytes()))
        cls.delegator_address = str(cls.delegator_wallet.address())

        cfg = NetworkConfig(
            chain_id="testing",
            url="grpc+http://localhost:9090",
            fee_minimum_gas_price=1,
            fee_denomination="atestfet",
            staking_denomination="atestfet",
        )

        gov_cfg = grpc.insecure_channel('localhost:9090')

        cls.ledger_client = LedgerClient(cfg)
        cls.gov_module = query_pb2_grpc.QueryStub(gov_cfg)

        cls.db = psycopg.connect(
            host="localhost",
            port="5432",
            dbname="postgres",
            user="postgres",
            password="postgres",
            options=f'-c search_path=app'
        )

        cls.db_cursor = cls.db.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()


class GovernanceTests(Base):
    vote_tx = None

    def setUp(self):
        self.msg = gov_tx.MsgVote(
            proposal_id=1,
            voter=self.validator_address,
            option=gov_pb2.VoteOption.VOTE_OPTION_YES
        )
        self.vote_tx = Transaction()
        self.vote_tx.add_message(self.msg)

    def testGovernanceProposal(self):
        proposal_content = any_pb2.Any()
        proposal_content.Pack(gov_pb2.TextProposal(
            title="Test Proposal",
            description="This is a test proposal"
        ), "")

        msg = gov_tx.MsgSubmitProposal(
            content=proposal_content,
            initial_deposit=[coin_pb2.Coin(
                denom="atestfet",
                amount="10000000"
            )],
            proposer=self.validator_address
        )

        tx = Transaction()
        tx.add_message(msg)

        tx = utils.prepare_and_broadcast_basic_transaction(self.ledger_client, tx, self.validator_wallet)
        tx.wait_to_complete()

        response = self.gov_module.Proposal(gov_query.QueryProposalRequest(proposal_id=1))
        print(response)
        self.assertIsNotNone(response)  # add assertion here

    # def testNoVotesYet(self):
    #     response = self.gov_module.TallyResult(gov_query.QueryTallyResultRequest(proposal_id=1))
    #     # parsed_response = json.loads(str(response))
    #
    #     transaction = self.db_cursor.execute('SELECT * from gov_proposal_votes').fetchone()

    def testSubmitVote(self):
        tx = utils.prepare_and_broadcast_basic_transaction(self.ledger_client, self.vote_tx, self.validator_wallet)
        tx.wait_to_complete()

        response = self.gov_module.TallyResult(gov_query.QueryTallyResultRequest(proposal_id=1))
        # parsed_response = json.loads(str(response))

        transaction = self.db_cursor.execute('SELECT * from gov_proposal_votes').fetchone()
        self.assertEqual(transaction[3], 'YES')


class DelegatorTests(Base):
    def setUp(self):
        delegate_tx = self.ledger_client.delegate_tokens(self.validator_operator_address, 100000, self.delegator_wallet)
        delegate_tx.wait_to_complete()

    def testClaimRewards(self):
        claim_tx = self.ledger_client.claim_rewards(self.validator_operator_address, self.delegator_wallet)
        claim_tx.wait_to_complete()

        transaction = self.db_cursor.execute('SELECT * from dist_delegator_claims').fetchone()
        self.assertEqual(transaction[1], self.delegator_address)

        undelegate_tx = self.ledger_client.undelegate_tokens(self.validator_operator_address, 100000, self.delegator_wallet)
        undelegate_tx.wait_to_complete()


class TransactionTests(Base):
    def testNativeTransfer(self):
        amount = 1000
        denom = "atestfet"
        msg_type = '/cosmos.bank.v1beta1.MsgSend'

        print(self.db_cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'app'").fetchall())

        tx = self.ledger_client.send_tokens(self.delegator_wallet.address(), amount, denom, self.validator_wallet)
        tx.wait_to_complete()

        transaction = self.db_cursor.execute('SELECT * from native_transfers').fetchone()
        print(transaction[1]['amount'][0]['amount'])

        self.assertEqual(transaction[1]['amount'][0]['amount'], str(amount))
        self.assertEqual(transaction[1]['amount'][0]['denom'], denom)
        self.assertEqual(transaction[1]['toAddress'], self.delegator_address)
        self.assertEqual(transaction[1]['fromAddress'], self.validator_address)


class LegacyBridgeSwapTests(Base):
    contract = None

    def setUp(self):
        url = "https://github.com/fetchai/fetch-ethereum-bridge-v1/releases/download/v0.2.0/bridge.wasm"
        if not os.path.exists("../.contract"):
            os.mkdir("../.contract")
        try:
            temp = open("../.contract/bridge.wasm", "rb")
            temp.close()
        except:
            contract_request = requests.get(url)
            open("../.contract/bridge.wasm", "wb").write(contract_request.content)
        self.contract = LedgerContract("../.contract/bridge.wasm", self.ledger_client)

    def testDeployContract(self):
        self.contract.deploy(
            {"cap": "250000000000000000000000000",
             "reverse_aggregated_allowance": "3000000000000000000000000",
             "reverse_aggregated_allowance_approver_cap": "3000000000000000000000000",
             "lower_swap_limit": "1",
             "upper_swap_limit": "1000000000000000000000000",
             "swap_fee": "0",
             "paused_since_block": 18446744073709551615,
             "denom": "atestfet",
             "next_swap_id": 0
             },
            self.validator_wallet
        )

    def testContractSwap(self):
        self.contract.execute(
            {"swap": {"destination": self.validator_address}},
            self.validator_wallet,
            funds="10000atestfet"
        )


if __name__ == '__main__':
    unittest.main()
