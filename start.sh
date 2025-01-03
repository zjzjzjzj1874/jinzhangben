#!/bin/bash

# 检查并启动 MongoDB
if ! pgrep -x "mongod" > /dev/null; then
    echo "启动 MongoDB..."
    mongod --fork --logpath /var/log/mongodb/mongod.log
fi

# 启动 Streamlit 应用
streamlit run app.py
