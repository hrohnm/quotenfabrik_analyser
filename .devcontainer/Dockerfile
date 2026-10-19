FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# The base image ships a Yarn apt repository whose signing key has expired (NO_PUBKEY 62D54FD4003F6525).
# Every "apt-get update" - also inside dev container features - fails until it is removed.
RUN rm -f /etc/apt/sources.list.d/yarn.list
