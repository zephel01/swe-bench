# Bug: a final release sorts before its own prereleases

`sort_versions(["1.0.0", "1.0.0-rc.1", "1.0.0-alpha", "1.0.0-beta"])` returns
`["1.0.0", "1.0.0-alpha", "1.0.0-beta", "1.0.0-rc.1"]`. The finished release
`1.0.0` ends up first, but it should come **last**, after all of its
prereleases. Equivalently `compare("1.0.0", "1.0.0-alpha")` returns `-1` when it
should be `1`.

Core numeric ordering and ordering among prerelease identifiers are correct.
