#!/bin/bash
python -m flask --app src.nonogram.admin.app run --host=0.0.0.0 --port=$PORT
