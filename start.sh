#!/bin/bash

# Start tabpy
tabpy &

# Wait for tabpy server to bootup
sleep 3

# Deploy models
tabpy-deploy-models &

wait