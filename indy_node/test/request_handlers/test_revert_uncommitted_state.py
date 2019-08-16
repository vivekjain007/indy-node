import functools
import time

import pytest

from indy_common.constants import CONFIG_LEDGER_ID
from indy_common.state import config
from indy_node.test.request_handlers.test_update_state_config_req_handler import prepare_request
from plenum.server.consensus.ordering_service import OrderingService
from plenum.server.replica import Replica
from plenum.test.testing_utils import FakeSomething


@pytest.fixture
def fake_ordering_service(config_ledger,
                 config_state,
                 db_manager):
    ordering_service = FakeSomething(db_manager=db_manager,
                                     post_batch_rejection=lambda *args, **kwargs: True,
                                     _logger=FakeSomething(info=lambda *args, **kwargs: True))
    ordering_service.l_revert = functools.partial(OrderingService.l_revert, ordering_service)
    return ordering_service


def test_revert_uncommitted_state(write_manager,
                                  db_manager,
                                  constraint_serializer,
                                  prepare_request,
                                  fake_ordering_service,
                                  tmpdir_factory):
    action, constraint, request = prepare_request
    req_count = 1

    state_root_hash_before = db_manager.get_state(CONFIG_LEDGER_ID).headHash

    write_manager.apply_request(request, int(time.time()))
    """
    Check, that request exist in uncommitted state
    """
    from_state = db_manager.get_state(CONFIG_LEDGER_ID).get(
        config.make_state_path_for_auth_rule(action.get_action_id()),
        isCommitted=False)
    assert constraint_serializer.deserialize(from_state) == constraint

    fake_ordering_service.l_revert(CONFIG_LEDGER_ID,
                                   state_root_hash_before,
                                   req_count)
    """
    Txn is reverted from ledger and state
    """
    assert len(db_manager.get_ledger(CONFIG_LEDGER_ID).uncommittedTxns) == 0
    from_state = db_manager.get_state(CONFIG_LEDGER_ID).get(
        config.make_state_path_for_auth_rule(action.get_action_id()),
        isCommitted=False)
    assert from_state is None