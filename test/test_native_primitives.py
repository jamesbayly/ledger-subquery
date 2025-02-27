import json

from gql import gql

import time
import unittest

import base
from helpers.field_enums import BlockFields, TxFields, MsgFields, EventFields
from helpers.regexes import block_id_regex, tx_id_regex, msg_id_regex, event_id_regex


class TestNativePrimitives(base.Base):
    tables = ("blocks", "transactions", "messages", "events")

    amount = 5000000
    denom = "atestfet"

    expected_blocks_len = 2
    expected_txs_len = 2
    expected_msgs_len = 2
    expected_msg_type_url = '/cosmos.bank.v1beta1.MsgSend'
    # NB: for each transfer:
    #   - coin_received
    #   - coin_spent
    #   - message
    #   - transfer
    expected_events_len = 2 * 4

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.clean_db()

        tx = cls.ledger_client.send_tokens(cls.delegator_address, cls.amount, cls.denom, cls.validator_wallet)
        tx.wait_to_complete()
        cls.assertTrue(tx.response.is_successful(), f"first set-up tx failed")

        tx = cls.ledger_client.send_tokens(cls.validator_address, int(cls.amount / 10), cls.denom, cls.delegator_wallet)
        tx.wait_to_complete()
        cls.assertTrue(tx.response.is_successful(), f"second set-up tx failed")

        # Wait for subql node to sync
        time.sleep(5)

    def test_blocks(self):
        blocks = self.db_cursor.execute(BlockFields.select_query()).fetchall()
        self.assertNotEqual(blocks, [], f"\nDBError: block table is empty - maybe indexer did not find an entry?")

        self.assertGreaterEqual(len(blocks), self.expected_blocks_len)
        for block in blocks:
            # NB: continually increments while test run
            self.assertGreaterEqual(len(blocks), 2)
            self.assertRegex(block[BlockFields.id.value], block_id_regex)
            # TODO: expect proper chainId
            self.assertNotEqual(block[BlockFields.chain_id.value], "")
            self.assertTrue(block[BlockFields.height.value] > 0)
            # TODO: assert timestamp within last 5 min
            # TODO: timestamp is a number
            self.assertNotEqual(block[BlockFields.timestamp.value], "")

    def test_blocks_query(self):
        query = gql("""
            query {
                blocks {
                    nodes {
                        id,
                        chainId,
                        height,
                        timestamp
                    }
                }
            }
        """)

        result = self.gql_client.execute(query)
        blocks = result["blocks"]["nodes"]
        self.assertIsNotNone(blocks)
        self.assertGreater(len(blocks), 0)

        for block in blocks:
            # TODO: expect proper chainId
            self.assertNotEqual(block["chainId"], "")
            self.assertGreater(int(block["height"]), 0)
            # TODO: timestamp should be unix timestamp
            self.assertNotEqual(block["timestamp"], "")

    def test_transactions(self):
        txs = self.db_cursor.execute(TxFields.select_query()).fetchall()
        self.assertEqual(len(txs), self.expected_txs_len)
        for tx in txs:
            self.assertRegex(tx[TxFields.id.value], tx_id_regex)
            self.assertTrue(len(tx[TxFields.block_id.value]) == 64)
            self.assertGreater(tx[TxFields.gas_used.value], 0)
            self.assertGreater(tx[TxFields.gas_wanted.value], 0)
            tx_signer_address = tx[TxFields.signer_address.value]
            self.assertTrue(tx_signer_address == self.validator_address or
                            tx_signer_address == self.delegator_address)

            fees = json.loads(tx[TxFields.fees.value])
            self.assertEqual(len(fees), 1)
            self.assertEqual(fees[0]["denom"], self.denom)
            self.assertGreater(int(fees[0]["amount"]), 0)
            self.assertEqual(tx[TxFields.memo.value], "")
            self.assertEqual(tx[TxFields.status.value], "Success")
            self.assertNotEqual(tx[TxFields.log.value], "")

    def test_transactions_query(self):
        query = gql("""
            query {
                transactions {
                    nodes {
                        id
                        block {
                            id
                        }
                        gasUsed
                        gasWanted
                        signerAddress
                        # TODO:
                        # fees
                    }
                }
            }
        """)

        result = self.gql_client.execute(query)
        txs = result["transactions"]["nodes"]
        self.assertIsNotNone(txs)
        self.assertEqual(len(txs), self.expected_txs_len)

        for tx in txs:
            self.assertRegex(tx["id"], tx_id_regex)
            self.assertRegex(tx["block"]["id"], block_id_regex)
            self.assertGreater(int(tx["gasUsed"]), 0)
            self.assertGreater(int(tx["gasWanted"]), 0)
            self.assertTrue(tx["signerAddress"] == self.validator_address or
                            tx["signerAddress"] == self.delegator_address)
            # TODO: fees

    def test_messages(self):

        msgs = self.db_cursor.execute(MsgFields.select_query()).fetchall()
        self.assertEqual(len(msgs), self.expected_msgs_len)
        for msg in msgs:
            self.assertRegex(msg[MsgFields.id.value], msg_id_regex)
            self.assertRegex(msg[MsgFields.transaction_id.value], tx_id_regex)
            self.assertNotEqual(msg[MsgFields.block_id.value], "")
            self.assertEqual(msg[MsgFields.type_url.value], self.expected_msg_type_url)
            self.assertNotEqual(msg[MsgFields.json.value], "")

    def test_messages_query(self):
        query_all = gql("""
            query {
                messages {
                    nodes {
                        id
                        block {
                            id
                        }
                        transaction {
                            id
                        }
                        typeUrl
                        json
                    }
                }
            }
        """)

        result = self.gql_client.execute(query_all)
        msgs = result["messages"]["nodes"]
        self.assertIsNotNone(msgs)
        self.assertEqual(len(msgs), self.expected_msgs_len)

        for msg in msgs:
            self.assertRegex(msg["id"], msg_id_regex)
            self.assertRegex(msg["block"]["id"], block_id_regex)
            self.assertRegex(msg["transaction"]["id"], tx_id_regex)
            self.assertEqual(msg["typeUrl"], self.expected_msg_type_url)
            # TODO: assert on parsed json (?)
            self.assertNotEqual(msg["json"], "")

    def test_messages_by_tx_signer_query(self):
        for address in [self.validator_address, self.delegator_address]:
            query_by_tx_signer = gql("""
                query {
                    messages (filter:  {transaction: {signerAddress: {equalTo: """ + json.dumps(address) + """}}}) {
                        nodes {
                            transaction {
                                signerAddress
                            }
                        }
                    }
                }
            """)

            result = self.gql_client.execute(query_by_tx_signer)
            msgs = result["messages"]["nodes"]
            self.assertIsNotNone(msgs)
            self.assertEqual(len(msgs), self.expected_msgs_len / 2)

            for msg in msgs:
                self.assertEqual(msg["transaction"]["signerAddress"], address)

    def test_events(self):
        events = self.db_cursor.execute(EventFields.select_query()).fetchall()
        self.assertEqual(len(events), self.expected_events_len)
        for event in events:
            self.assertRegex(event[EventFields.id.value], event_id_regex)
            self.assertRegex(event[EventFields.transaction_id.value], tx_id_regex)
            self.assertNotEqual(event[EventFields.block_id.value], "")
            self.assertNotEqual(event[EventFields.type.value], "")
            # TODO: more assertions (?)

    def test_events_query(self):
        query = gql("""
            query {
                events {
                    nodes {
                        id
                        block {
                            id
                        }
                        transaction {
                            id
                        }
                        attributes
                    }
                }
            }
        """)

        result = self.gql_client.execute(query)
        events = result["events"]["nodes"]
        self.assertIsNotNone(events)
        self.assertEqual(len(events), self.expected_events_len)

        for event in events:
            self.assertRegex(event["id"], event_id_regex)
            self.assertRegex(event["block"]["id"], block_id_regex)
            self.assertRegex(event["transaction"]["id"], tx_id_regex)

            attributes = event["attributes"]
            self.assertGreater(len(attributes), 0)
            for attr in attributes:
                for field in ["key", "value"]:
                    self.assertTrue(field in list(attr))
                    self.assertNotEqual(attr[field], "")

                # These three event types have an "amount" key/value
                if attr["key"] in ["coin_spent", "coin_received", "transfer"]:
                    self.assertEqual(attr["value"], f"{self.amount}{self.denom}")


if __name__ == '__main__':
    unittest.main()
