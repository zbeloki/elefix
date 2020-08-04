import setuptools

setuptools.setup(
    name="elevfix",
    version="0.0.1",
    author="Zuhaitz Beloki",
    author_email="zbeloki@gmail.com",
    description="",
    long_description="",
    long_description_content_type="text/markdown",
    url="https://github.com/zbeloki/elevfix",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[],
    packages=setuptools.find_packages(),
    scripts=[
        'bin/srtm_asc_to_bin.py'
    ],
)
