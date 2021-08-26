#!/bin/bash

# Start tabpy
tabpy &

# Wait for server to become available, wait 1 min maximum
attempt_counter=0
max_attempts=20

until $(curl --output /dev/null --silent --head --fail localhost:9004); do
    if [ ${attempt_counter} -eq ${max_attempts} ];then
      echo "Maximum attempts reached, tabpy server not started"
      exit 1
    fi

    echo "Waiting for tabpy server"
    attempt_counter=$(($attempt_counter+1))
    sleep 3
done

# Deploy tabpy models
tabpy-deploy-models &
wait