from python:3.8.12-alpine

WORKDIR /admission-controller

RUN python -m pip install flask==2.0.2 kubernetes==19.15.0

COPY ./server.py /admission-controller

ENV FLASK_ENV development

ENTRYPOINT [ "python" ]

CMD [ "server.py" ]

