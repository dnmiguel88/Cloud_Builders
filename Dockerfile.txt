FROM registry.access.redhat.com/ubi9/python-311
COPY app.py .
ENV DATA_DIR=/data
EXPOSE 8080
CMD ["python", "app.py"]
