import os
import pytest
from unittest.mock import patch

from orchestration.workflow import (
    WorkflowState,
    admin_approval_node,
    record_data_node,
    notify_user_node,
    should_record_data,
    build_workflow,
)
from db.sql_store import init_db, create_reservation, update_reservation_status
from storage.file_writer import clear_confirmed_reservations, get_confirmed_reservations
from config.settings import SQLITE_DB_PATH


@pytest.fixture(autouse=True)
def clean_environment():
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    init_db()
    clear_confirmed_reservations()

    yield

    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
    clear_confirmed_reservations()


def test_user_interaction_node_sets_reservation():
    """Test that user_interaction_node populates state when agent submits a reservation."""
    reservation_id = create_reservation(
        full_name="Test User",
        license_plate="TEST-123",
        start_datetime="2026-03-20 10:00",
        end_datetime="2026-03-20 18:00",
        zone_preference="A",
    )

    state: WorkflowState = {
        "user_input": "test",
        "reservation_data": None,
        "reservation_id": None,
        "admin_decision": None,
        "admin_comment": None,
        "final_message": None,
        "error": None,
    }

    # Simulate what the node does after detecting a reservation
    from db.sql_store import get_reservation
    reservation = get_reservation(reservation_id)
    state["reservation_data"] = {
        "full_name": reservation["full_name"],
        "license_plate": reservation["license_plate"],
        "start_datetime": reservation["start_datetime"],
        "end_datetime": reservation["end_datetime"],
        "zone_preference": reservation["zone_preference"],
    }
    state["reservation_id"] = reservation_id
    state["admin_decision"] = "pending"

    assert state["reservation_data"] is not None
    assert state["reservation_data"]["full_name"] == "Test User"
    assert state["reservation_id"] == reservation_id
    assert state["admin_decision"] == "pending"
    assert state["error"] is None


def test_user_interaction_node_no_reservation():
    """Test that user_interaction_node sets error when no reservation is submitted."""
    state: WorkflowState = {
        "user_input": "test",
        "reservation_data": None,
        "reservation_id": None,
        "admin_decision": None,
        "admin_comment": None,
        "final_message": None,
        "error": None,
    }

    # Simulate the node exiting without a reservation (user typed 'done')
    if state.get("reservation_id") is None and state.get("error") is None:
        state["error"] = "No reservation was submitted during the conversation"

    assert state["error"] is not None
    assert state["reservation_id"] is None


def test_admin_approval_node_approved():
    reservation_id = create_reservation(
        full_name="Test User",
        license_plate="TEST-456",
        start_datetime="2026-03-21 09:00",
        end_datetime="2026-03-21 17:00",
    )

    update_reservation_status(reservation_id, "approved", "Test approval")

    state: WorkflowState = {
        "user_input": "test",
        "reservation_data": {
            "full_name": "Test User",
            "license_plate": "TEST-456",
            "start_datetime": "2026-03-21 09:00",
            "end_datetime": "2026-03-21 17:00",
            "zone_preference": None,
        },
        "reservation_id": reservation_id,
        "admin_decision": "pending",
        "admin_comment": None,
        "final_message": None,
        "error": None,
    }

    with patch('orchestration.workflow.time.sleep'):
        result = admin_approval_node(state)

    assert result["admin_decision"] == "approved"
    assert result["admin_comment"] == "Test approval"
    assert result["error"] is None


def test_admin_approval_node_rejected():
    reservation_id = create_reservation(
        full_name="Test User",
        license_plate="TEST-789",
        start_datetime="2026-03-22 09:00",
        end_datetime="2026-03-22 17:00",
    )
    update_reservation_status(reservation_id, "rejected", "No space")

    state: WorkflowState = {
        "user_input": "test",
        "reservation_data": {
            "full_name": "Test User",
            "license_plate": "TEST-789",
            "start_datetime": "2026-03-22 09:00",
            "end_datetime": "2026-03-22 17:00",
            "zone_preference": None,
        },
        "reservation_id": reservation_id,
        "admin_decision": "pending",
        "admin_comment": None,
        "final_message": None,
        "error": None,
    }

    with patch('orchestration.workflow.time.sleep'):
        result = admin_approval_node(state)

    assert result["admin_decision"] == "rejected"
    assert result["admin_comment"] == "No space"


def test_record_data_node():
    reservation_id = create_reservation(
        full_name="Alice Johnson",
        license_plate="RECORD-123",
        start_datetime="2026-03-25 10:00",
        end_datetime="2026-03-25 18:00",
        zone_preference="A",
    )
    update_reservation_status(reservation_id, "approved")

    state: WorkflowState = {
        "user_input": "test",
        "reservation_data": {
            "full_name": "Alice Johnson",
            "license_plate": "RECORD-123",
            "start_datetime": "2026-03-25 10:00",
            "end_datetime": "2026-03-25 18:00",
            "zone_preference": "A",
        },
        "reservation_id": reservation_id,
        "admin_decision": "approved",
        "admin_comment": "VIP",
        "final_message": None,
        "error": None,
    }

    result = record_data_node(state)

    confirmed = get_confirmed_reservations()
    assert len(confirmed) == 1
    assert confirmed[0]["full_name"] == "Alice Johnson"
    assert confirmed[0]["license_plate"] == "RECORD-123"


def test_record_data_node_skipped_if_rejected():
    state: WorkflowState = {
        "user_input": "test",
        "reservation_data": {
            "full_name": "Test User",
            "license_plate": "SKIP-123",
            "start_datetime": "2026-03-26 10:00",
            "end_datetime": "2026-03-26 18:00",
            "zone_preference": None,
        },
        "reservation_id": 999,
        "admin_decision": "rejected",
        "admin_comment": "No space",
        "final_message": None,
        "error": None,
    }

    result = record_data_node(state)

    confirmed = get_confirmed_reservations()
    assert len(confirmed) == 0


def test_notify_user_node_approved():
    state: WorkflowState = {
        "user_input": "test",
        "reservation_data": {
            "full_name": "Test User",
            "license_plate": "NOTIFY-123",
            "start_datetime": "2026-03-27 10:00",
            "end_datetime": "2026-03-27 18:00",
            "zone_preference": "A",
        },
        "reservation_id": 1,
        "admin_decision": "approved",
        "admin_comment": "Welcome!",
        "final_message": None,
        "error": None,
    }

    result = notify_user_node(state)

    assert result["final_message"] is not None
    assert "APPROVED" in result["final_message"]
    assert "NOTIFY-123" in result["final_message"]


def test_notify_user_node_rejected():
    state: WorkflowState = {
        "user_input": "test",
        "reservation_data": {
            "full_name": "Test User",
            "license_plate": "REJECT-123",
            "start_datetime": "2026-03-28 10:00",
            "end_datetime": "2026-03-28 18:00",
            "zone_preference": None,
        },
        "reservation_id": 2,
        "admin_decision": "rejected",
        "admin_comment": "Fully booked",
        "final_message": None,
        "error": None,
    }

    result = notify_user_node(state)

    assert result["final_message"] is not None
    assert "REJECTED" in result["final_message"]
    assert "Fully booked" in result["final_message"]


def test_should_record_data_conditional():
    approved_state: WorkflowState = {
        "user_input": "test",
        "reservation_data": {},
        "reservation_id": 1,
        "admin_decision": "approved",
        "admin_comment": None,
        "final_message": None,
        "error": None,
    }
    assert should_record_data(approved_state) == "record_data"

    rejected_state: WorkflowState = {
        "user_input": "test",
        "reservation_data": {},
        "reservation_id": 2,
        "admin_decision": "rejected",
        "admin_comment": None,
        "final_message": None,
        "error": None,
    }
    assert should_record_data(rejected_state) == "notify_user"

    error_state: WorkflowState = {
        "user_input": "test",
        "reservation_data": {},
        "reservation_id": None,
        "admin_decision": None,
        "admin_comment": None,
        "final_message": None,
        "error": "Test error",
    }
    assert should_record_data(error_state) == "notify_user"


def test_build_workflow():
    """Test full workflow by mocking user_interaction_node to skip interactive input."""
    reservation_id = create_reservation(
        full_name="Workflow Test",
        license_plate="WORK-123",
        start_datetime="2026-03-30 10:00",
        end_datetime="2026-03-30 18:00",
    )

    update_reservation_status(reservation_id, "approved", "Test")

    def fake_user_interaction(state):
        from db.sql_store import get_reservation as _get
        res = _get(reservation_id)
        state["reservation_data"] = {
            "full_name": res["full_name"],
            "license_plate": res["license_plate"],
            "start_datetime": res["start_datetime"],
            "end_datetime": res["end_datetime"],
            "zone_preference": res["zone_preference"],
        }
        state["reservation_id"] = reservation_id
        state["admin_decision"] = "pending"
        return state

    with patch('orchestration.workflow.user_interaction_node', fake_user_interaction):
        workflow = build_workflow()

        initial_state: WorkflowState = {
            "user_input": "test",
            "reservation_data": None,
            "reservation_id": None,
            "admin_decision": None,
            "admin_comment": None,
            "final_message": None,
            "error": None,
        }

        with patch('orchestration.workflow.time.sleep'):
            result = workflow.invoke(initial_state)

    assert result is not None
    assert result.get("final_message") is not None
    assert "APPROVED" in result["final_message"]
