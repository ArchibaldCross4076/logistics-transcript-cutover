from src.logistics_service import decide_event


def test_damaged_delivery_becomes_exception_for_operations() -> None:
    event = decide_event("Delivered, but the carton is damaged and needs inspection.", "SHP-1042")

    assert event.shipment_id == "SHP-1042"
    assert event.event == "exception"
    assert event.exception == "inspect parcel before release"
