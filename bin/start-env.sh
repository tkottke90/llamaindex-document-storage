#! /bin/bash

docker run -it --rm -v "$PWD:/usr/app" --workdir="/usr/app" python:3.11 /bin/bash