
FROM python:alpine3.9
RUN apk add --update --no-cache --virtual .tmp-build-deps \
    gcc libc-dev linux-headers postgresql-dev \
    && apk add libffi-dev
COPY . /app
WORKDIR /app
RUN export GOOGLE_APPLICATION_CREDENTIALS="./keys.json"
RUN pip3 install --upgrade pip
RUN pip3 install wheel
RUN pip3 install -r requirements.txt 
EXPOSE 8080
ENTRYPOINT [ "python" ] 
CMD [ "main.py" ] 
