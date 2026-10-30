from math import ceil


def total_pages(total_records: int, per_page: int) -> int:
    return ceil(total_records / per_page)
