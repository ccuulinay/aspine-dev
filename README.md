Aspine
========
Aspine: A simple python native implementation of data caching

What is it?
========
Aspine provide a simple in-memory data store, used as caching and data synchronization。


Installation
========
Use the [pip](https://pip.pypa.io/en/stable/) to install aspine.

```bash
pip install aspine
```

Usage
========

### A simple example

```python
# save this as server.py
from aspine import AspineServer

if __name__ == "__main__":
    # Please change host, port, authkey for your aspine server.
    # Default host is 127.0.0.1
    # Default port is 5116
    # Default authkey is 123456
    m = AspineServer()
    m.run()
```

Then run it.
```bash
python server.py
```

From where you want to use your aspine server.
```python
from aspine import AspineClient

cli = AspineClient()
cli.connect()

cli.set("this_is_key", "this is value")
cli.set("sample_key", {"a": 1, "b": "text here"})
```

You could get it back anywhere once you connect to it.
```python
>>> from aspine import AspineClient
>>> 
>>> cli = AspineClient()
>>> cli.connect()
>>> cli.get("sample_key")
{'name': 'sample_key', 'value': {'a': 1, 'b': 'text here'}, 'set_ts': 1646215110.250738}
```

## License
[MIT](https://github.com/ccuulinay/aspine-dev/blob/main/LICENSE)