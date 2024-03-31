def calculate_avg(series):
    return calculate_sum(series) / calculate_len(series) if calculate_len(series) else 0

def calculate_sum(series):
    return sum(series)

def calculate_len(series):
    return len(series)
