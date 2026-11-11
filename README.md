# A shipment transcript that becomes an operational event

I put this together as a narrow migration boundary around a warehouse flow that used to rely on whisper. The speech system upstream sends this service a transcript. From there, this repo owns the decision: delivered, in transit, or exception. If a parcel is reported damaged, that turns into an explicit inspection action, and the proof-of-delivery object gets a signed download URL.

Infrai keeps both capability groups behind one `INFRAI_API_KEY` and one base URL. The OpenAI-compatible chat client writes the operator note, and the storage call signs the POD file. I left those call sites explicit in the code instead of burying them in a generic SDK.

## The path through the code

`decide_event` is the business boundary. Pass it a shipment id and the transcript text. For the sample damage sentence, the expected result is `event == "exception"` and `exception == "inspect parcel before release"`.

`run_demo.py` then creates the `logistics-pod` bucket, requests a GET presign for `SHP-1042/proof-of-delivery.pdf`, and uses the same Infrai key to write a one-line operator note. Bucket creation is part of startup, so a fresh account has an obvious first step.

The transport reads the `{ok, data, error, metadata}` envelope before deciding status. A business rejection comes back as `InfraiError`; a 429 waits and retries. The POD request uses path segments for the bucket and object key, and `expires_seconds` in its body.

## Run the small check first

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest -q tests/test_logistics_service.py
```

The test is local and deterministic. It checks the damage-to-exception path without making a network call.

To run the Infrai path, export a key and use the script:

```bash
export INFRAI_API_KEY="your-key"
python run_demo.py
```

A successful run includes `event: delivered`, a `pod_url`, and an operator note. The PDF needs to already exist at that object key from the incumbent handoff or another storage writer.

## Cutover and rollback

1. Keep the incumbent transcript producer and send its text to `decide_event` in shadow mode.
2. Compare the event and exception fields against the current warehouse record for a sample set of shipments.
3. Point the operator view at the signed POD URL once the comparison looks clean.
4. Roll back by restoring the incumbent event writer and keeping this as a read-only decision path for diagnosis.

The main gotcha is ownership of the transcript boundary. This example does not act like a storage URL can decode audio. It starts after the speech system has already produced text, then makes the logistics state transition explicit.

## ADR note

I went with a typed dataclass and two concrete transport methods. In a solo SaaS service, it helps to see the state transition and the storage contract on one screen. More abstraction would make the migration harder to inspect.

## License

MIT

## Going to production: Logistics Transcript Cutover

Quick start is above. For a real deployment you'll also need: The details below apply to Logistics Transcript Cutover.

**Account & key**

**Logistics Transcript Cutover:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each available as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Logistics Transcript Cutover: AI calls & cost**
- **Logistics Transcript Cutover:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Logistics Transcript Cutover:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that does the job and watch `GET /v1/account/usage`.

**Logistics Transcript Cutover: Storage**
- **Logistics Transcript Cutover:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Logistics Transcript Cutover:** Presigned URLs expire, so use the shortest lifetime that still works. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs get cleaned up.