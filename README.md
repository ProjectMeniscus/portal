# Meniscus Portal
Moving data quickly

## Building Portal
```bash
pip install -r tools/pip-requires
pip install -r tools/test-requires
python setup.py build_ext --inplace
nosetests
```
