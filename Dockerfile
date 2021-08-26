FROM python:3

WORKDIR /app

# install the latest TabPy
RUN python3 -m pip install --upgrade pip && python3 -m pip install --upgrade tabpy

# start TabPy
CMD ["sh", "-c", "tabpy"]

# run startup script
ADD start.sh /
RUN chmod +x /start.sh
CMD ["/start.sh"]
