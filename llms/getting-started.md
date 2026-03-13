# data.bs.ch: Getting Started for LLMs

This guide explains how to discover datasets and retrieve records from `data.bs.ch` using Huwise Explore API v2.1 endpoints.

## API basics

- Base portal: `https://data.bs.ch`
- Explore API base path: `https://data.bs.ch/api/explore/v2.1`
- Main discovery endpoint: `GET /catalog/datasets`
- Main records endpoint: `GET /catalog/datasets/{dataset_id}/records`

All examples below are URL-encoded and safe to copy/adapt.

## Fast discovery flow

1. List datasets with minimal metadata:

`https://data.bs.ch/api/explore/v2.1/catalog/datasets?select=dataset_id%2Cmetas.default.title&limit=20&offset=0`

2. Inspect one dataset schema and metadata:

`https://data.bs.ch/api/explore/v2.1/catalog/datasets/{dataset_id}`

3. Pull first records:

`https://data.bs.ch/api/explore/v2.1/catalog/datasets/{dataset_id}/records?limit=10`

4. Add ODSQL clauses for filtering and aggregation:

`https://data.bs.ch/api/explore/v2.1/catalog/datasets/{dataset_id}/records?select=count(*)%20as%20n&group_by=year(date_field)&order_by=year(date_field)%20asc`

## Pagination and limits

- Use `limit` and `offset`.
- For records queries without `group_by`, `limit` max is generally 100.
- For grouped queries, higher limits can be available (up to 20000 in v2.1 behavior).
- If you need full extraction, prefer export endpoints over repeated small page pulls.

## Safe query construction rules

- Start simple (`limit`, then `select`, then `where`, then `group_by`/`order_by`).
- Encode spaces and operators in URLs.
- Quote string literals in ODSQL (for example `"Basel"`).
- When a field name is also an ODSQL keyword, wrap it in backticks.
- Keep one concern per query while exploring (discovery, filtering, or aggregation).

## Useful companion documents

- [ODSQL cheat sheet](https://raw.githubusercontent.com/opendatabs/data.bs.ch_llms.txt/refs/heads/main/llms/odsql-cheatsheet.md)
- [Query cookbook](https://raw.githubusercontent.com/opendatabs/data.bs.ch_llms.txt/refs/heads/main/llms/query-cookbook.md)
- [Dataset index](https://raw.githubusercontent.com/opendatabs/data.bs.ch_llms.txt/refs/heads/main/llms/datasets/index.md)
- [Official ODS Explore API v2.1 documentation](https://help.opendatasoft.com/apis/ods-explore-v2/)
- [OpenAPI specification download entrypoint](https://help.opendatasoft.com/apis/ods-explore-v2/): open the docs page and use "Download OpenAPI specification".
