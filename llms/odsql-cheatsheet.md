# ODSQL Cheat Sheet for data.bs.ch

This is a practical subset of ODSQL for reliable query generation against `data.bs.ch`.

Use with:

- `GET /api/explore/v2.1/catalog/datasets`
- `GET /api/explore/v2.1/catalog/datasets/{dataset_id}/records`

For full details, see the official reference:  
<https://help.opendatasoft.com/apis/ods-explore-v2/>

## Common clauses

- `select`: fields, computed expressions, and aggregations
- `where`: filters and predicates
- `group_by`: grouping keys
- `order_by`: sort by fields or aggregations
- `limit`, `offset`: pagination

## Query patterns

### Select fields

- `select=field1,field2`
- `select=field1 as label1,field2`

### Filter rows

- `where=population > 10000`
- `where=country_code = "CH"`
- `where=search(*, "basel")`

### Aggregate

- `select=count(*) as n`
- `select=sum(amount) as total`
- `select=year(date_field) as y,count(*) as n&group_by=y`

### Sort

- `order_by=field1 asc`
- `order_by=count(*) desc`

## URL-encoded examples

- Count rows:
  `?select=count(*)%20as%20n`
- Filter + sort:
  `?where=country_code%20%3D%20%22CH%22&order_by=population%20desc&limit=10`
- Group by year:
  `?select=year(date_field)%20as%20y%2Ccount(*)%20as%20n&group_by=y&order_by=y%20asc`

## Frequent pitfalls

- Use `where=...` for row filtering, not `refine` if you need precise ODSQL logic.
- `AND`/`OR` precedence matters; use parentheses for clarity.
- String comparisons are case-sensitive unless you normalize with functions like `lower(...)`.
- `startswith(...)` is case-sensitive.
- Keep `order_by` expressions valid for grouped queries (aggregations first when mixed).
- Avoid unencoded spaces or reserved characters in URLs.

## Minimal troubleshooting checklist

1. Remove clauses until the query works, then re-add one by one.
2. Confirm field names from dataset schema endpoint.
3. Verify quotes around string literals.
4. Re-check URL encoding.
5. Validate function availability for the chosen clause.
