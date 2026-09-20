# D1 Test Cases

## Test 1 — Mock run
Run with no API keys. Expected:
- app opens
- sample leads appear
- duplicate company variant is removed
- every lead receives a deterministic score
- CSV buttons work

## Test 2 — robots.txt
Use a public URL that disallows the test user-agent in robots.txt.
Expected:
- no page request is made
- URL appears in compliance log

## Test 3 — Duplicate domain
Create two records with the same website domain.
Expected:
- one record retained

## Test 4 — Duplicate email
Create two records with the same email.
Expected:
- one record retained

## Test 5 — Missing evidence
Set industry or employee count to Unknown/0.
Expected:
- no points are awarded for missing evidence

## Test 6 — Export
Download both CSVs.
Expected:
- standard CSV contains lead, source, score and reasoning fields
- HubSpot-style CSV contains company/contact columns

## Test 7 — Refresh
Run the same ICP twice.
Expected:
- search/page cache is reused where available
- duplicate records do not accumulate
