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
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import grpc, json, time, unittest, psycopg, os, requests
unittest.TestLoader.sortTestMethodsUsing = lambda *args: 1


class Base(unittest.TestCase):
    delegator_wallet = None
    delegator_address = None

    validator_wallet = None
    validator_address = None
    validator_operator_address = None

    ledger_client = None
    db = None
    db_cursor = None
    gql_client = None

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

        transport = AIOHTTPTransport(url="http://localhost:3000")
        cls.gql_client = Client(transport=transport, fetch_schema_from_transport=True)

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
    denom = "atestfet"
    amount = "10000000"
    option = "YES"

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
                denom=self.denom,
                amount=self.amount
            )],
            proposer=self.validator_address
        )

        tx = Transaction()
        tx.add_message(msg)

        tx = utils.prepare_and_broadcast_basic_transaction(self.ledger_client, tx, self.validator_wallet)
        tx.wait_to_complete()
        self.assertTrue(tx.response.is_successful())
        # response = self.gov_module.Proposal(gov_query.QueryProposalRequest(proposal_id=1))

    def testProposalVote(self):
        self.db_cursor.execute('TRUNCATE table gov_proposal_votes')
        self.db.commit()
        self.assertFalse(self.db_cursor.execute('SELECT * from gov_proposal_votes').fetchall())

        tx = utils.prepare_and_broadcast_basic_transaction(self.ledger_client, self.vote_tx, self.validator_wallet)
        tx.wait_to_complete()
        self.assertTrue(tx.response.is_successful())

        time.sleep(5)

        row = self.db_cursor.execute('SELECT * from gov_proposal_votes').fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[3], self.option)

    def testRetrieveVote(self):
        query = gql(
            """
            query getGovernanceVotes {
                govProposalVotes {
                    nodes {
                        transactionId
                        voterAddress
                        option
                        }
                    }
                }
            """
        )

        result = self.gql_client.execute(query)
        self.assertEqual(result["govProposalVotes"]["nodes"][0]["option"], self.option)
        self.assertEqual(result["govProposalVotes"]["nodes"][0]["voterAddress"], self.validator_address)


class DelegatorTests(Base):
    amount = 100

    def setUp(self):
        delegate_tx = self.ledger_client.delegate_tokens(self.validator_operator_address, self.amount, self.delegator_wallet)
        delegate_tx.wait_to_complete()
        self.assertTrue(delegate_tx.response.is_successful())

    def testClaimRewards(self):
        self.db_cursor.execute('TRUNCATE table dist_delegator_claims')
        self.db.commit()

        claim_tx = self.ledger_client.claim_rewards(self.validator_operator_address, self.delegator_wallet)
        claim_tx.wait_to_complete()
        self.assertTrue(claim_tx.response.is_successful())

        time.sleep(5)

        row = self.db_cursor.execute('SELECT * from dist_delegator_claims').fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], self.delegator_address)

    def testRetrieveClaim(self):
        query = gql(
            """
            query getDelegatorRewardClaim {
                distDelegatorClaims {
                    nodes {
                        transactionId
                        delegatorAddress
                        validatorAddress
                        }
                    }
                }
            """
        )

        result = self.gql_client.execute(query)
        self.assertEqual(result["distDelegatorClaims"]["nodes"][0]["delegatorAddress"], self.delegator_address)
        self.assertEqual(result["distDelegatorClaims"]["nodes"][0]["validatorAddress"], self.validator_operator_address)


class TransactionTests(Base):
    amount = 5000000
    denom = "atestfet"
    msg_type = '/cosmos.bank.v1beta1.MsgSend'

    def testNativeTransfer(self):

        self.db_cursor.execute('TRUNCATE table native_transfers')
        self.db.commit()

        tx = self.ledger_client.send_tokens(self.delegator_wallet.address(), self.amount, self.denom, self.validator_wallet)
        tx.wait_to_complete()
        self.assertTrue(tx.response.is_successful())

        time.sleep(5)

        row = self.db_cursor.execute('SELECT * from native_transfers').fetchone()

        self.assertIsNotNone(row)

        self.assertEqual(row[1]['amount'][0]['amount'], str(self.amount))
        self.assertEqual(row[1]['amount'][0]['denom'], self.denom)
        self.assertEqual(row[1]['toAddress'], self.delegator_address)
        self.assertEqual(row[1]['fromAddress'], self.validator_address)

    def testRetrieveTransfer(self):
        query = gql(
            """
            query getNativeTransfers {
                nativeTransfers {
                    nodes {
                        transactionId
                        message 
                        }
                    }
                }
            """
        )

        result = self.gql_client.execute(query)
        self.assertEqual(result["nativeTransfers"]["nodes"][0]["message"]["amount"][0]["denom"], self.denom)
        self.assertEqual(result["nativeTransfers"]["nodes"][0]["message"]["amount"][0]["amount"], str(self.amount))
        self.assertEqual(result["nativeTransfers"]["nodes"][0]["message"]["toAddress"], self.delegator_address)
        self.assertEqual(result["nativeTransfers"]["nodes"][0]["message"]["fromAddress"], self.validator_address)


class LegacyBridgeSwapTests(Base):
    contract = None
    amount = "10000"
    denom = "atestfet"

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
        self.db_cursor.execute('TRUNCATE table legacy_bridge_swaps')
        self.db.commit()
        self.assertFalse(self.db_cursor.execute('SELECT * from legacy_bridge_swaps').fetchall())

        self.contract.execute(
            {"swap": {"destination": self.validator_address}},
            self.validator_wallet,
            funds=str(self.amount)+self.denom
        )

        time.sleep(12)

        row = self.db_cursor.execute('SELECT * from legacy_bridge_swaps').fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], self.validator_address)

    def testRetrieveSwap(self):
        query = gql(
            """
            query getLegacyBridgeSwaps {
                legacyBridgeSwaps {
                    nodes {
                        transactionId
                        destination
                        amount
                        denom
                        }
                    }
                }
            """
        )

        result = self.gql_client.execute(query)
        self.assertEqual(result["legacyBridgeSwaps"]["nodes"][0]["destination"], self.validator_address)
        self.assertEqual(result["legacyBridgeSwaps"]["nodes"][0]["amount"], self.amount)
        self.assertEqual(result["legacyBridgeSwaps"]["nodes"][0]["denom"], self.denom)


if __name__ == '__main__':
    unittest.main()
