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
    for i, line in enumerate(f):
      if i < start:
        continue
      if i > end:
        break
      lines[i] = line.rstrip('\n')

  return lines
