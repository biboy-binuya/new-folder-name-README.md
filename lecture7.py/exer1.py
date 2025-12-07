foods = ("pizza", "burger", "fries", "salad", "ice cream")

print("Original menu:")
for food in foods:
    print(food)

try:
    foods[1] = "hot dog"
except TypeError as e:
    print("\nError: Tuples are immutable, cannot change items!")
    print("Details:", e)

foods = ("sushi", "ramen", "tempura", "onigiri", "mochi")

print("\nRevised menu:")
for food in foods:
    print(food)
