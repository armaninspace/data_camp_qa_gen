#!/usr/bin/env bash

mkdir -p tmp/local tmp/pnpm-home tmp/pnpm-store tmp/npm-cache
docker run --rm -it \
  --init \
  --ipc=host \
  --mount type=bind,src="$PWD",dst=/code \
  -w /code \
  -p 127.0.0.1:8921:8821 \
  -p 127.0.0.1:8922:8922 \
  -p 127.0.0.1:8923:8923 \
  data_camp_exp
