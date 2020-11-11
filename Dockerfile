FROM python:3

WORKDIR /app

# install the latest TabPy
RUN python3 -m pip install --upgrade pip && python3 -m pip install --upgrade tabpy

# start TabPy
CMD ["sh", "-c", "tabpy"]

# deploy models
RUN tabpy-deploy-models
