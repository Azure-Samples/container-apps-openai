#!/bin/bash

# Variables
source ./00-variables.sh

# Login to ACR
echo "Logging in to [${acrName,,}] container registry..."
az acr login --name ${acrName,,}

# Retrieve ACR login server. Each container image needs to be tagged with the loginServer name of the registry. 
echo "Retrieving login server for the [${acrName,,}] container registry..."
loginServer=$(az acr show --name ${acrName,,} --query loginServer --output tsv)

# Use a for loop to tag and push the local docker images to the Azure Container Registry
for index in ${!images[@]}; do
  # Tag the local sender image with the loginServer of ACR
  docker tag ${images[$index],,}:$tag $loginServer/${images[$index],,}:$tag

  # Push the container image to ACR
  docker push $loginServer/${images[$index],,}:$tag
done