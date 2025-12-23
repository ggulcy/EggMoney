target = 625
times = 5
multiplier = 1.3

initial = (target+10) / (multiplier ** times)
print(f"목표값: {target+10} ÷ {multiplier}^{times} = 초기값: {initial:.2f}")
print()

value = initial
for i in range(times + 1):
    print(f"{i}회: {value:.2f}")
    value *= multiplier
