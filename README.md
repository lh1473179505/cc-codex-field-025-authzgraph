# authzgraph

A relationship-tuple authorization engine in the style of a small Zanzibar/SpiceDB subset.

`python -m authzgraph inspect --namespace fixtures/namespace.json --tuples fixtures/tuples/owners.tsv` already loads the graph. `check` is still a stub: it has to walk union, exclusion, parent usersets, cycles, depth caps, and caveats.

Standard library only. No Docker, no SpiceDB, no graph databases.
