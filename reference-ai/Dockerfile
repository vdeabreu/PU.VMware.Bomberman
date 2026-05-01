FROM python:3.11-slim

WORKDIR /app
COPY strategy.py bot.py ./

EXPOSE 8080
ENV PYTHONUNBUFFERED=1
CMD ["python", "bot.py"]
