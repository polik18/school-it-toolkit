#!/bin/bash
# school-mac-admin pip wrapper
# Automatically appends --user to pip install commands to prevent permission errors on macOS

ARGS=()
HAS_INSTALL=false
HAS_USER=false

for arg in "$@"; do
  if [ "$arg" = "install" ]; then
    HAS_INSTALL=true
  fi
  if [ "$arg" = "--user" ]; then
    HAS_USER=true
  fi
  ARGS+=("$arg")
done

if [ "$HAS_INSTALL" = true ] && [ "$HAS_USER" = false ]; then
  # Do not add --user if we are asking for help or running uninstall/etc.
  # We check if there is an install command.
  # pip install options that don't support --user: -h, --help
  IS_HELP=false
  for arg in "$@"; do
    if [ "$arg" = "-h" ] || [ "$arg" = "--help" ]; then
      IS_HELP=true
    fi
  done
  if [ "$IS_HELP" = false ]; then
    ARGS+=("--user")
  fi
fi

exec /usr/bin/pip3 "${ARGS[@]}"
