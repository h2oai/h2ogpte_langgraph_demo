setup:
	uv sync
	cp .env.example .env
	uv run python3 create_collections.py

run:
	uv run langgraph dev
