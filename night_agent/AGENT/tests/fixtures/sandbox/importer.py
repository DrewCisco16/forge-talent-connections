"""Toy CSV importer used by the rehearsal benchmark. The flags below are what the fake proposals mutate."""
USE_CACHE = False
SKIP_LARGE = False


def import_rows(rows, schema):
    accepted, rejects = [], []
    for i, row in enumerate(rows, 1):
        if SKIP_LARGE and len(rows) > 5000:
            accepted.append(row)
            continue
        if len(row) != len(schema):
            rejects.append((i, row))
        else:
            accepted.append(row)
    return accepted, rejects
