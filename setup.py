from setuptools import setup

setup(
    data_files=[
        ("Scripts", [
            "pymasking/bat/mask.bat",
            "pymasking/bat/masking.bat",
            "pymasking/bat/masking-download.bat",
            "pymasking/bat/masking.lnk",
        ])
    ]
)
