# Query Cookbook for data.bs.ch

Ready-to-adapt Explore API v2.1 examples for `data.bs.ch`.

Base: `https://data.bs.ch/api/explore/v2.1`

## 1) List datasets with IDs and titles

`/catalog/datasets?select=dataset_id%2Cmetas.default.title&limit=20&offset=0`

## 2) Find datasets by keyword

`/catalog/datasets?where=search(*%2C%20%22verkehr%22)&select=dataset_id%2Cmetas.default.title&limit=25`

## 3) Inspect one dataset schema

`/catalog/datasets/{dataset_id}`

## 4) Fetch first records

`/catalog/datasets/{dataset_id}/records?limit=10`

## 5) Return only specific columns

`/catalog/datasets/{dataset_id}/records?select=field_a%2Cfield_b&limit=20`

## 6) Apply a numeric filter

`/catalog/datasets/{dataset_id}/records?where=value_field%20%3E%20100&limit=20`

## 7) Apply date range filter

`/catalog/datasets/{dataset_id}/records?where=date_field%20IN%20%5Bdate'2023-01-01'%20..%20date'2023-12-31'%5D&limit=100`

## 8) Aggregate and group by year

`/catalog/datasets/{dataset_id}/records?select=year(date_field)%20as%20y%2Ccount(*)%20as%20n&group_by=y&order_by=y%20asc&limit=100`

## 9) Top categories by count

`/catalog/datasets/{dataset_id}/records?select=category_field%2Ccount(*)%20as%20n&group_by=category_field&order_by=n%20desc&limit=20`

## 10) Sum a metric by category

`/catalog/datasets/{dataset_id}/records?select=category_field%2Csum(amount_field)%20as%20total&group_by=category_field&order_by=total%20desc&limit=20`

## 11) Case-insensitive match (via lower)

`/catalog/datasets/{dataset_id}/records?where=lower(name_field)%20%3D%20%22basel%22&limit=20`

## 12) Prefix search

`/catalog/datasets/{dataset_id}/records?where=startswith(name_field%2C%20%22Bas%22)&limit=20`

## 13) Full-text fuzzy search

`/catalog/datasets/{dataset_id}/records?where=search(*%2C%20%22rhein%20ufer%22)&limit=20`

## 14) Distinct count estimate

`/catalog/datasets/{dataset_id}/records?select=count(distinct%20field_name)%20as%20unique_values`

## 15) Get complete export instead of paging

`/catalog/datasets/{dataset_id}/exports/csv?select=field1%2Cfield2&where=status%20%3D%20%22active%22`

## Common LLM query errors and fixes

- Error: Unknown field name.
  - Fix: Inspect `/catalog/datasets/{dataset_id}` and copy exact `name` values.
- Error: ODSQL malformed.
  - Fix: Simplify to one clause, then incrementally add `where`, `group_by`, `order_by`.
- Error: Empty result unexpectedly.
  - Fix: Check string casing and quote style; test without `where`.
- Error: Too few rows returned.
  - Fix: Adjust `limit`/`offset`, or switch to exports endpoint for full data extraction.
- Error: Bad date filtering.
  - Fix: Use explicit date literals like `date'YYYY-MM-DD'`.
