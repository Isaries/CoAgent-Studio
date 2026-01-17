.PHONY: lint format

lint:
	ruff check .

format:
	black .

type-check:
	mypy .

test-docker:
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

clean-docker:
	docker-compose -f docker-compose.test.yml down -v

worker:
	arq app.worker.WorkerSettings --watch app
