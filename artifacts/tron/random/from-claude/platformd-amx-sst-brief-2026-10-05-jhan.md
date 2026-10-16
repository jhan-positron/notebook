# Enable AMX

## enable build option
I am not sure if you are the right person to do this. By default AMX feature is not built, it is controlled by build flag TRON_AMX_DISPATCH. https://github.com/positron-ai/tron/pull/4505/changes turned it on in the `deb` preset. The product apt package is built with the same preset (`make deb`, nightly and version tags), so the released package already carries AMX since tron 2026.09.23. Only a product binary built outside `make deb` would still lack it. I do not know if such a build exists (do you know who should I talk to?)

## AMX environment variable
Nothing needs to be set to enable AMX. When the binary has AMX built in, AMX is on at run time by default. TRON_AMX_DISABLE=1 (exactly "1") turns it off. The variable is read once, at the first attention call, so we will need to restart product if we change its value.

# Intel speed select

This is more involved than AMX, and Hannah and I did it differently since she did it for nightly CI and I did it as development.

## install binary
Intel speed select is GPL license source code from Intel, the binary is built and installed at delphi-3bda, /opt/intel-speed-select/intel-speed-select (Hannah's CI installed it at /etc/default/intel-speed-select-state). This binary needs to install at all OCI machines. It is not harmful to install at andoria.

## execute intel-speed-select
I have a shell script to run it, Hannah's CI used ansible, here is the PR, https://github.com/positron-ai/positron-infrastructure/pull/165. The ansible installs a systemd oneshot service, intel-speed-select-state, that applies the config from /etc/default/intel-speed-select-state at every boot.

Please let me know platformd expectation.

## execute at system boot up
speed select config is not persistent across boots, so we need to run it each time system boots up. On delphi-3bda the service above already does this.
