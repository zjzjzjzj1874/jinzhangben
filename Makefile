.PHONY: build dev run rebuild rebuild-fresh restart logs local-run local-restart

# OrbStack / Docker（Compose V2 插件：docker compose）
COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml
LOCAL_COMPOSE_FILE := docker-compose.local.yml

# 本地直接运行 Streamlit（不经过容器）
build:
	streamlit run app.py
dev: build

# 首次或常规启动 compose（后台）
run:
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

# 修改代码后使 web 生效：重建镜像并重建容器
# 注意：docker-compose.yml 未挂载源码，仅 restart 不会加载新代码
rebuild:
	$(COMPOSE) -f $(COMPOSE_FILE) up -d --build web

# 强制无缓存重建（怀疑镜像缓存未更新时使用）
rebuild-fresh:
	$(COMPOSE) -f $(COMPOSE_FILE) build --no-cache web
	$(COMPOSE) -f $(COMPOSE_FILE) up -d web

# 仅重启 web（不重新 build，代码变更不会生效）
restart:
	$(COMPOSE) -f $(COMPOSE_FILE) restart web

logs:
	$(COMPOSE) -f $(COMPOSE_FILE) logs -f web

# 本地开发 compose（挂载 .:/app，改代码后 restart 即可）
local-run:
	$(COMPOSE) -f $(LOCAL_COMPOSE_FILE) up -d

local-restart:
	$(COMPOSE) -f $(LOCAL_COMPOSE_FILE) restart web
