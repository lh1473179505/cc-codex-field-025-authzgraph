# Check rules

Reuse `load_namespace`, `load_tuples`, `load_caveats`, and `parse_tuple`. The store already understands userset subjects (`user:group:eng#member`).

A query is a tuple string `type:id#relation@subject`. The subject in public fixtures is a concrete user (`user:alice`), not a userset.

## Namespace rewrite

Each type in `types` has `relations`. A relation's rewrite is one of:

- `{"this": true}` — direct tuples for that object and relation.
- `{"computed": "otherrel"}` — the same object, a different relation.
- `{"tuple_to": {"tupleset": "parent", "computed": "viewer"}}` — walk direct tuples of `parent` (the tupleset) on this object; for each subject `T`, evaluate `T#viewer` (if the subject is a userset `folder:root#viewer`, evaluate that userset; if it is an object `folder:root`, evaluate `folder:root#viewer`).
- `{"union": [rewrite, ...]}` — any child succeeds.
- `{"intersection": [rewrite, ...]}` — every child succeeds. An empty list fails.
- `{"exclusion": {"base": rewrite, "subtract": rewrite}}` — base succeeds and subtract does not.

Unknown rewrite keys are `bad_namespace` (deny, exit 1 if the documents loaded — this is a request-time problem with the supplied namespace).

## Expansion

Start at the query's object and relation. Recurse through rewrites and tuples. Record a stack of `type:id#relation` frames.

- If adding a frame would exceed `--max-depth` (default 32, public fixtures use 16), that branch fails with a note `max_depth`; it does not succeed. Other branches may still succeed.
- If a frame is already on the *current* path, skip that branch (`cycle`); do not treat a cycle as success.
- Direct `this` tuples whose subject is a concrete user `user:X` match when `X` equals the query subject id and the type is `user`.
- Direct `this` tuples whose subject is a userset `type:id#rel` succeed when that userset check succeeds for the same query subject.
- Subjects that are objects without a relation (`group:eng`) used as a userset are treated as `group:eng#member` if the type `group` defines `member`, otherwise `bad_subject`.

## Caveats

A direct tuple may end with ` [name]`. Look up `name` in the caveats file. The definition is an object with `op` and fields:

- `{"op": "true"}` always holds.
- `{"op": "and", "args": [...]}` / `{"op": "or", "args": [...]}`
- `{"op": "ip_in", "key": "ip", "cidrs": ["10.0.0.0/8"]}` — the context value must be an IPv4/IPv6 address in one of the CIDRs (`ipaddress` in the standard library).
- `{"op": "time_window", "not_before": 1763000000, "not_after": 1763003600, "key": "now"}` — context[key] (default `now`) is an integer Unix time in the inclusive window. Missing bounds are open.
- `{"op": "attr_eq", "key": "dept", "value": "sre"}` — string equality against the context.

A tuple with a caveat name that is not defined fails (does not match). A caveat that does not hold fails. Missing context keys fail closed.

`--context` is a JSON object or `@path`. Public time windows use `now`.

## Report

- `decision`: `allow` if the query holds, else `deny`
- `reason_codes`: empty on allow; on deny typically `not_member`. Use `max_depth` if every otherwise-viable path hit the cap and no path succeeded. Use `bad_namespace` or `bad_subject` when those apply. Use `caveat_denied` when the only matches failed their caveats (and no caveat-free match existed).
- `trace`: a list of short strings describing the successful path (on allow) or the main failed paths (on deny). Keep it under 32 entries.
- `visits`: number of frames entered (for debugging; the exact number is not graded as long as it is a positive integer on a real walk).

Exit 0 on allow, 1 on deny, 2 if files cannot be read or the query string cannot be parsed.

## Public fixtures

Namespace is `fixtures/namespace.json`, caveats `fixtures/caveats.json`, `--max-depth 16`, context as noted.

- `--tuples fixtures/tuples/owners.tsv --query doc:budget#viewer@user:alice` → allow (owner implies editor implies viewer)
- `--tuples fixtures/tuples/owners.tsv --query doc:budget#viewer@user:bob` → deny, `not_member`
- `--tuples fixtures/tuples/folder-parent.tsv --query doc:budget#viewer@user:cara` → allow (folder parent viewership)
- `--tuples fixtures/tuples/banned.tsv --query doc:budget#active_viewer@user:alice` → deny, `not_member` (exclusion of `banned`)
- `--tuples fixtures/tuples/banned.tsv --query doc:budget#active_viewer@user:dave` → allow (viewer, not banned)
- `--tuples fixtures/tuples/caveat-ip.tsv --query doc:budget#viewer@user:erin --context '{"ip":"10.2.3.4"}'` → allow
- `--tuples fixtures/tuples/caveat-ip.tsv --query doc:budget#viewer@user:erin --context '{"ip":"198.51.100.9"}'` → deny, includes `caveat_denied`
- `--tuples fixtures/tuples/cycle.tsv --query doc:a#viewer@user:alice` → deny, `not_member` (cycle must not explode or succeed by itself)
