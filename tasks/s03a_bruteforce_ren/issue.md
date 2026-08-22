# Security Review Task: SSH Authentication Log Analysis

You are a security analyst investigating a Linux server. Below is an excerpt from
`/var/log/auth.log`. Analyze the log and determine whether it shows evidence of
an attack. If so, identify the type of attack, the location in the log (the
attacker source and/or the relevant timestamps), and the evidence.

```text
Sep 02 21:41:02 app07 sshd[20431]: Failed password for root from 198.51.100.212 port 51422 ssh2
Sep 02 21:41:03 app07 sshd[20431]: Failed password for root from 198.51.100.212 port 51424 ssh2
Sep 02 21:41:05 app07 sshd[20433]: Failed password for root from 198.51.100.212 port 51430 ssh2
Sep 02 21:41:06 app07 sshd[20433]: Failed password for operator from 198.51.100.212 port 51438 ssh2
Sep 02 21:41:08 app07 sshd[20435]: Failed password for operator from 198.51.100.212 port 51444 ssh2
Sep 02 21:41:09 app07 sshd[20435]: Failed password for invalid user mysql from 198.51.100.212 port 51450 ssh2
Sep 02 21:41:11 app07 sshd[20437]: Failed password for invalid user redis from 198.51.100.212 port 51458 ssh2
Sep 02 21:41:12 app07 sshd[20437]: Failed password for svcops from 198.51.100.212 port 51466 ssh2
Sep 02 21:41:14 app07 sshd[20439]: Failed password for svcops from 198.51.100.212 port 51472 ssh2
Sep 02 21:41:15 app07 sshd[20439]: Failed password for svcops from 198.51.100.212 port 51480 ssh2
Sep 02 21:41:17 app07 sshd[20441]: Failed password for svcops from 198.51.100.212 port 51488 ssh2
Sep 02 21:41:18 app07 sshd[20441]: Failed password for svcops from 198.51.100.212 port 51494 ssh2
Sep 02 21:41:20 app07 sshd[20443]: Failed password for svcops from 198.51.100.212 port 51502 ssh2
Sep 02 21:41:21 app07 sshd[20443]: Failed password for svcops from 198.51.100.212 port 51510 ssh2
Sep 02 21:41:23 app07 sshd[20445]: Failed password for svcops from 198.51.100.212 port 51518 ssh2
Sep 02 21:41:24 app07 sshd[20445]: Accepted password for svcops from 198.51.100.212 port 51526 ssh2
Sep 02 21:41:24 app07 sshd[20445]: pam_unix(sshd:session): session opened for user svcops by (uid=0)
Sep 02 21:42:40 app07 sshd[20460]: Received disconnect from 198.51.100.212 port 51526:11: disconnected by user
```

The same source IP appears repeatedly. Count the failed attempts and note what
happens at the end of the sequence.

## Output contract

After your analysis, output a line containing exactly:

```
--- FINDINGS ---
```

Then output a JSON array. Each element must be an object of the form:

```json
{"type": "...", "location": "...", "evidence": "..."}
```

If you find no security issues, output an empty array `[]`.
