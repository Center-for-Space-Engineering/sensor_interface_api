# tests/conftest.py
import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def change_to_src_dir():
    # Set working directory to "src"
    if 'src' not in os.getcwd():
        src_path = os.path.abspath("src")
        os.chdir(src_path)