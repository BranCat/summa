from summa_python_interface import J

base = [7.5e-06, 0.55, 1.3]
a = J(base)
b = J([7.5e-05, 0.55, 1.3])
c = J(base)

print(f"first  J(base) = {a}")
print(f"middle J(other)= {b}")
print(f"again  J(base) = {c}")
print("REPEATABLE" if a == c else "STATE LEAK - a and c differ")
