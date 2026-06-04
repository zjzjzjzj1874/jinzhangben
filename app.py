"""Streamlit 入口（根目录保留，便于 docker / streamlit run app.py）。"""
from bill_tracker.ui.app import main

if __name__ == '__main__':
    main()
