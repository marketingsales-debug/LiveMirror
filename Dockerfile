FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy backend
COPY backend/ ./backend/
COPY src/ ./src/

# Install dependencies
RUN cd backend && uv sync

# Copy frontend build (built separately)
COPY frontend/dist/ ./frontend/dist/

EXPOSE 5001 3000

CMD ["sh", "-c", "cd backend && uv run python run.py"]
