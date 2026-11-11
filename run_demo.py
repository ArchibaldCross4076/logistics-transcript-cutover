"""Runnable cutover smoke path for one shipment."""

from src.logistics_service import InfraiTransport, decide_event, explain_event


def main() -> None:
    shipment_id = "SHP-1042"
    transcript = "Driver says the parcel was delivered and signed at the receiving desk."
    event = decide_event(transcript, shipment_id)
    transport = InfraiTransport()
    transport.ensure_bucket("logistics-pod")
    pod_url = transport.presign_pod("logistics-pod", f"{shipment_id}/proof-of-delivery.pdf")
    print({"event": event.event, "pod_url": pod_url, "operator_note": explain_event(event)})


if __name__ == "__main__":
    main()
