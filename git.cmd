@echo off
:: git.cmd — commitguard Windows PATH shim
::
:: Placed at the beginning of the user PATH so the OS resolves 'git'
:: to this script before finding the real git.exe.
::
:: All git commands are forwarded to git_guard.py which handles
:: validation for 'git commit' and transparent passthrough for everything else.
python "%~dp0git_guard.py" %*
