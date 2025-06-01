FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy source code
COPY pyproject.toml ./

RUN python -c "import tomllib; deps = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; print('\n'.join(deps))" > requirements.txt

# Install dependencies using pip from the requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY crawler.py .
# COPY .env .

# Command
CMD ["python3", "crawler.py"]