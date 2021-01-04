#!/bin/bash

for f in *.epub; do
  python3 charactergraph.py "$f" --output="$f.eps"
done
