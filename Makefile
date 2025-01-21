

build:
	streamlit run app.py

run:
	podman compose -f docker-compose.yml up -d

local-run:
	podman compose -f docker-compose.local.yml up -d

