def geometric_mean(values):
    product = 1.0
    for v in values:
        product *= v
    return product ** (1.0 / len(values))
