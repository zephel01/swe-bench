# Bug: the shortest-path search takes edges it was told to avoid

`shortest_path` is given a set of `forbidden` edges that must not be used, yet it
still routes through them. In the sample graph, `shortest_path(g, "a", "d",
forbidden={("b", "c")})` returns `3` by going through the banned `b->c` edge; the
correct answer that respects the ban is `5`.

Plain shortest paths and unreachable cases already work.
