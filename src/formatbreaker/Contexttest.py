from formatbreaker import util

a = util.Context({"a": 3})


print(a["a"])

a["foo"] = 54
a["foo"] = 55

print(a)

b = dict(a)

print(b)

print(b.keys())
