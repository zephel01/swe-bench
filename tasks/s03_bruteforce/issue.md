# Security Review Task: SSH Authentication Log Analysis

You are a security analyst investigating a Linux server. Below is an excerpt from
`/var/log/auth.log`. Analyze the log and determine whether it shows evidence of
an attack. If so, identify the type of attack, the location in the log (the
attacker source and/or the relevant timestamps), and the evidence.

```text
Jul 18 03:11:02 web01 sshd[20431]: Failed password for root from 203.0.113.66 port 51422 ssh2
Jul 18 03:11:03 web01 sshd[20431]: Failed password for root from 203.0.113.66 port 51424 ssh2
Jul 18 03:11:05 web01 sshd[20433]: Failed password for root from 203.0.113.66 port 51430 ssh2
Jul 18 03:11:06 web01 sshd[20433]: Failed password for admin from 203.0.113.66 port 51438 ssh2
Jul 18 03:11:08 web01 sshd[20435]: Failed password for admin from 203.0.113.66 port 51444 ssh2
Jul 18 03:11:09 web01 sshd[20435]: Failed password for invalid user oracle from 203.0.113.66 port 51450 ssh2
Jul 18 03:11:11 web01 sshd[20437]: Failed password for invalid user postgres from 203.0.113.66 port 51458 ssh2
Jul 18 03:11:12 web01 sshd[20437]: Failed password for deploy from 203.0.113.66 port 51466 ssh2
Jul 18 03:11:14 web01 sshd[20439]: Failed password for deploy from 203.0.113.66 port 51472 ssh2
Jul 18 03:11:15 web01 sshd[20439]: Failed password for deploy from 203.0.113.66 port 51480 ssh2
Jul 18 03:11:17 web01 sshd[20441]: Failed password for deploy from 203.0.113.66 port 51488 ssh2
Jul 18 03:11:18 web01 sshd[20441]: Failed password for deploy from 203.0.113.66 port 51494 ssh2
Jul 18 03:11:20 web01 sshd[20443]: Failed password for deploy from 203.0.113.66 port 51502 ssh2
Jul 18 03:11:21 web01 sshd[20443]: Failed password for deploy from 203.0.113.66 port 51510 ssh2
Jul 18 03:11:23 web01 sshd[20445]: Failed password for deploy from 203.0.113.66 port 51518 ssh2
Jul 18 03:11:24 web01 sshd[20445]: Accepted password for deploy from 203.0.113.66 port 51526 ssh2
Jul 18 03:11:24 web01 sshd[20445]: pam_unix(sshd:session): session opened for user deploy by (uid=0)
Jul 18 03:12:40 web01 sshd[20460]: Received disconnect from 203.0.113.66 port 51526:11: disconnected by user
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
