

build:
	streamlit run app.py

local-run:
	docker-compose -f docker-compose.local.yml up -d

local-run-home:
	docker-compose -f docker-compose.local.home.yml up -d
local-run-com:
	docker-compose -f docker-compose.local.company.yml up -d
