FROM python:3.13-alpine
WORKDIR /app
COPY app.py ./
RUN mkdir /data && chown 1000:1000 /data
USER 1000:1000
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "app.py"]
