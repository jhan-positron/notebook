#!/bin/bash
# Print the number of established non-self client connections to :80,
# then the peer list. Self = loopback + every local address, in plain,
# bracketed-IPv6, or IPv4-mapped-IPv6 form.
ss -Htn state established "( sport = :80 )" 2>/dev/null | awk -v ips="127.0.0.1 ::1 $(hostname -I)" "
NF {
  p=\$NF; sub(/:[0-9]+\$/,\"\",p); gsub(/[][]/,\"\",p); sub(/^::ffff:/,\"\",p)
  n=split(ips,a,\" \"); self=0
  for(i=1;i<=n;i++) if(p==a[i]) self=1
  if(!self) { cnt++; peers=peers \" \" \$NF }
}
END { print cnt+0; if (cnt) print peers }"
