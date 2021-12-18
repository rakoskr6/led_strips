#!/usr/bin/env sh
amixer sget 'Capture' | grep 'Left' | grep '%' | sed -e 's/ \+/,/g' | cut -d',' -f 6 | sed -e 's|[][]||g' | sed -e 's/%//g'
