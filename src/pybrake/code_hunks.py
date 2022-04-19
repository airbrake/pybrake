from functools import lru_cache


@lru_cache(maxsize=1000)
def get_code_hunk(filename, lineno, nlines=2, loader=None, module_name=None):
    lines = _get_lines_from_file(filename, loader=loader, module_name=module_name)
    if lines is None:
        return None

    start = max(0, lineno - 1 - nlines)
    end = min(lineno + nlines, len(lines))
    hunk = {}
    for i, line in enumerate(lines[start:end], start + 1):
        if isinstance(line, bytes):
            line = line.decode("utf8", "replace")
        hunk[i] = line.rstrip("\n")

    return hunk


@lru_cache(maxsize=10)
def _get_lines_from_file(filename, loader=None, module_name=None):
    if loader is not None and hasattr(loader, "get_source"):
        try:
            source = loader.get_source(module_name)
        except ImportError:
            pass
        else:
            if source:
                return source.splitlines()

    try:
        with open(filename, "rb") as f:
            return f.read().splitlines()
    except (OSError, IOError):
        return None
