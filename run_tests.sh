#!/bin/bash

# Install required packages if not already installed
pip install -q requests uvicorn

# Stop any existing containers
docker-compose down

# Start the test database
echo "Starting test database..."
docker-compose up -d postgres_test

# Wait for database to be ready
echo "Waiting for database to be ready..."
for i in {1..30}; do
    if docker-compose exec -T postgres_test pg_isready -U postgres > /dev/null 2>&1; then
        echo "Database is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Database failed to start"
        docker-compose logs postgres_test
        exit 1
    fi
    echo "Waiting for database... ($i/30)"
    sleep 1
done

# Create test database if it doesn't exist
echo "Setting up test database..."
docker-compose exec -T postgres_test psql -U postgres -c "DROP DATABASE IF EXISTS app_test;"
docker-compose exec -T postgres_test psql -U postgres -c "CREATE DATABASE app_test;"

# Run the tests
echo "Running tests..."
pytest "$@" -v

# Stop the test database
echo "Cleaning up..."
docker-compose down 