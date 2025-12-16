.PHONY: help setup process process-all clean

help:
	@echo "Clothify - Image Processor"
	@echo ""
	@echo "Setup:"
	@echo "  make setup        - Create venv and install dependencies"
	@echo ""
	@echo "Usage:"
	@echo "  make process      - Process 1 random image"
	@echo "  make process-all  - Process all images"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        - Remove virtual environment"

setup:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r image-processor/requirements.txt
	@echo ""
	@echo "Setup complete! Run 'make process' to start."

process:
	.venv/bin/python image-processor/main.py

process-all:
	.venv/bin/python image-processor/main.py --all

clean:
	rm -rf .venv
	@echo "Virtual environment removed."
