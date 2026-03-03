# tests/test_sync.py
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest


SAMPLE_RESPONSE = {
    "accounts": [
        {
            "org": {"domain": "chase.com", "name": "Chase", "id": "chase-org-1"},
            "id": "acct-checking-1",
            "name": "TOTAL CHECKING",
            "currency": "USD",
            "balance": "4230.50",
            "available-balance": "4200.00",
            "balance-date": 1740873600,
            "transactions": [
                {
                    "id": "txn-1",
                    "posted": 1740787200,
                    "amount": "-47.32",
                    "description": "WHOLE FOODS MKT #10234",
                    "pending": False,
                },
                {
                    "id": "txn-2",
                    "posted": 1740700800,
                    "amount": "4225.00",
                    "description": "PAYROLL AMAZON",
                    "pending": False,
                },
            ],
        }
    ]
}


def test_parse_simplefin_response():
    from simledge.sync import parse_response
    institutions, accounts, balances, transactions = parse_response(SAMPLE_RESPONSE)

    assert len(institutions) == 1
    assert institutions[0]["id"] == "chase-org-1"
    assert institutions[0]["name"] == "Chase"

    assert len(accounts) == 1
    assert accounts[0]["id"] == "acct-checking-1"
    assert accounts[0]["name"] == "TOTAL CHECKING"
    assert accounts[0]["institution_id"] == "chase-org-1"

    assert len(balances) == 1
    assert balances[0]["balance"] == 4230.50

    assert len(transactions) == 2
    assert transactions[0]["amount"] == -47.32
    assert transactions[1]["amount"] == 4225.00


def test_parse_handles_missing_org():
    response = {
        "accounts": [
            {
                "id": "acct-1",
                "name": "Account",
                "currency": "USD",
                "balance": "100.00",
                "balance-date": 1740873600,
                "transactions": [],
            }
        ]
    }
    from simledge.sync import parse_response
    institutions, accounts, balances, transactions = parse_response(response)
    assert len(institutions) == 0
    assert accounts[0]["institution_id"] is None


def test_parse_handles_pending_transactions():
    response = {
        "accounts": [
            {
                "id": "acct-1",
                "name": "Account",
                "currency": "USD",
                "balance": "100.00",
                "balance-date": 1740873600,
                "transactions": [
                    {
                        "id": "txn-pending",
                        "posted": 1740787200,
                        "amount": "-10.00",
                        "description": "PENDING CHARGE",
                        "pending": True,
                    }
                ],
            }
        ]
    }
    from simledge.sync import parse_response
    _, _, _, transactions = parse_response(response)
    assert transactions[0]["pending"] is True
