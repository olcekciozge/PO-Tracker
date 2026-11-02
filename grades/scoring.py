def weighted_average(pairs):
    total_weight = sum(weight for weight, score in pairs)
    if total_weight == 0:
        return None
    weighted_sum = sum(weight * score for weight, score in pairs)
    return weighted_sum / total_weight