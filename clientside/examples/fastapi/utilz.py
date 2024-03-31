def calculate_avg(series):
    if calculate_len(series) == 0:
        return 0
    return calculate_sum(series) / calculate_len(series)


def calculate_sum(series):
    return sum(series)


def calculate_len(series):
    return len(series)
