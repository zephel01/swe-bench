# CIDR ranges are off by one and exclude their own endpoints

We work with IPv4 subnets in CIDR notation. `network_range(cidr)` returns the
`(network, broadcast)` integers for a block, and `contains(cidr, ip)` tests
membership. Two problems:

- The broadcast address of a block is wrong: for `192.168.1.0/24` we get an
  address past the end of the block instead of `192.168.1.255`.
- Membership treats the endpoints as outside the block: the network address
  itself is reported as not belonging to its own subnet.

Addresses well inside a block, and addresses far outside it, are classified
correctly.
