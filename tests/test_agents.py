from agents.rag_chain import (
    search_parking_info,
    get_pricing,
    ParkingReservation,
)


def test_tools_have_pydantic_schemas():
    """Verify tools have proper Pydantic input schemas."""
    assert search_parking_info.args_schema is not None
    assert get_pricing.args_schema is not None


def test_parking_reservation_model():
    """Test the ParkingReservation Pydantic model validates correctly."""
    reservation = ParkingReservation(
        full_name="John Smith",
        license_plate="ABC-1234",
        start_datetime="2026-03-05 10:00",
        end_datetime="2026-03-05 18:00",
        zone_preference="A",
    )
    assert reservation.full_name == "John Smith"
    assert reservation.license_plate == "ABC-1234"
    assert reservation.zone_preference == "A"
