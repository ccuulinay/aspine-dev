


# To build dist
python setup.py sdist bdist_wheel

# To check dist
twine check dist/*

# To upload to TestPyPi
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# To upload to PyPi
twine upload dist/prod_0.0.1/*

# Install it under standard pypi
pip install --index-url https://pypi.org/simple/ aspine