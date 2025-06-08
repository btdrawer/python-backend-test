# FastAPI Backend Service

Learning to build a Python backend using Cursor. (So far, the vast majority of this code is AI-generated.)

## Setup

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with the following variables:

```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
```

4. Initialize the database:

```bash
alembic upgrade head
```

## Running the Service

Development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000
API documentation will be available at http://localhost:8000/docs

## Development

- Format code: `black .`
- Run linter: `flake8`
- Run type checking: `mypy .`
- Run tests: `pytest`
