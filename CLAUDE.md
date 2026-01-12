# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

H1-Sponsors-Jobs is an H1B visa job board platform with a microservices architecture consisting of three components:

- **backend/**: FastAPI-based REST API service
- **scraper/**: Scrapy + Playwright web scraping service
- **infra/**: Docker Compose infrastructure configuration

## Architecture

The system uses a shared PostgreSQL database between backend and scraper components:

1. **Scraper** collects job postings from various websites and stores them in PostgreSQL
2. **Backend** serves the API, reads from PostgreSQL, and indexes data in Elasticsearch for search functionality
3. **Redis** is used for caching and task queuing
4. All services run in Docker containers and communicate via a bridge network

### Technology Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic (migrations), Pydantic, Uvicorn, Elasticsearch client
- **Scraper**: Scrapy, Playwright, BeautifulSoup4, SQLAlchemy (shared ORM)
- **Infrastructure**: PostgreSQL 16, Elasticsearch 8.11.0, Redis 7

## Development Commands

### Infrastructure Setup

```bash
# Start all infrastructure services (PostgreSQL, Elasticsearch, Redis)
docker-compose -f infra/docker-compose.yml up -d

# Stop all services
docker-compose -f infra/docker-compose.yml down

# View logs
docker-compose -f infra/docker-compose.yml logs -f [service_name]
```

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server (with auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic upgrade head                              # Apply migrations
alembic revision --autogenerate -m "description"  # Create new migration
alembic downgrade -1                              # Rollback one migration
```

### Scraper Development

```bash
cd scraper

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for JavaScript-heavy sites)
playwright install

# Run a spider
scrapy crawl <spider_name>

# List available spiders
scrapy list
```

## Database Connection Details

When infrastructure is running via docker-compose:

- **Host**: localhost
- **Port**: 5432
- **Database**: h1jobs
- **User**: h1user
- **Password**: h1pass (default, check docker-compose.yml)

Elasticsearch: http://localhost:9200
Redis: localhost:6379

## Key Architectural Notes

- Both backend and scraper use SQLAlchemy ORM with the same models, ensuring schema consistency
- Backend uses Alembic for database schema migrations
- Scraper writes directly to PostgreSQL; backend reads and indexes to Elasticsearch
- Pydantic is used for data validation and settings management in the backend
- The scraper uses Playwright for sites requiring JavaScript rendering, falling back to Scrapy's standard HTTP client for simpler sites
