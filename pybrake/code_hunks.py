from functools import lru_cache


NLINES = 2

@lru_cache(maxsize=1000)
def get_code_hunk(filename, line):
  start = line - NLINES
  end = line + NLINES

  try:
    f = open(filename)
  except Exception:
    return None

  lines = dict()
  with f:
    for lineno, line in enumerate(f, 1):
      if lineno < start:
        continue
      if lineno > end:
        break
      lines[lineno] = line.rstrip('\n')

  return lines
