def calculate_avg(series):
    if calculate_len(series) > 0:
        return calculate_sum(series) / calculate_len(series)
    else:
        return 0


def calculate_sum(series):
    return sum(series)


def calculate_len(series):
    return len(series)
