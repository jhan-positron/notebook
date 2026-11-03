#!/bin/bash
set -eu

if [ "$(id -u)" -ne 0 ]; then
    printf '%s\n' 'Run this script with sudo on phoenix-crb.' >&2
    exit 1
fi

if getent passwd jhan >/dev/null || getent group jhan >/dev/null || [ -e /home/jhan ]; then
    printf '%s\n' 'The jhan account, group, or home already exists. Stop and inspect it.' >&2
    exit 1
fi

useradd --create-home --shell /bin/bash --user-group --groups sudo jhan
install -d -o jhan -g jhan -m 0700 /home/jhan/.ssh
printf '%s\n' 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPQP2AIELQEZCHuHPN1U+oLXyak1GAcB99cRSJ0pGhv/ jhan@positron.ai (dev-server alpha)' > /home/jhan/.ssh/authorized_keys
chown jhan:jhan /home/jhan/.ssh/authorized_keys
chmod 0600 /home/jhan/.ssh/authorized_keys

printf '%s\n' 'Set the new password for jhan. Sudo will require this password.'
passwd jhan
id jhan
sudo -l -U jhan
printf '%s\n' 'Created jhan with the supplied SSH key and password-required sudo access.'
