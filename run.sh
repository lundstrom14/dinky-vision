#!/bin/bash
cd dinky_vision
uvicorn --host 0.0.0.0 main:app --reload --port 8080
