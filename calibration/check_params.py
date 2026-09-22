from summa_python_interface import J

base = [7.5e-06, 0.55, 1.3]
b = J(base)
print(f"base                       {b}")

for i, val in [(0, 7.5e-05), (1, 0.35), (2, 2.0)]:
    p = list(base)
    p[i] = val
    v = J(p)
    flag = "NO CHANGE" if v == b else "ok"
    print(f"param {i} = {val:<10}       {v}   {flag}")
