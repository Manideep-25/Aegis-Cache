.PHONY: proto dev test

proto:
	python -m grpc_tools.protoc \
		-I proto/ \
		--python_out=server/generated/ \
		--grpc_python_out=server/generated/ \
		proto/cache.proto
	touch server/__init__.py server/generated/__init__.py

test:
	pytest tests/ -v --asyncio-mode=auto

dev:
	python server/grpc_server.py \
		--host 0.0.0.0 --port 50051 \
		--capacity 256 --policy LRU \
		--redis redis://localhost:6379