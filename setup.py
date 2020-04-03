import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="hecss", # Replace with your own username
    version="0.2.0",
    author="Paweł T. Jochym",
    author_email="pawel.jochym@ifj.edu.pl",
    description="High Efficiency Configuration Space Sampler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/jochym/hecss",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPL3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)