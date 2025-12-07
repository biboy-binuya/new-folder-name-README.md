from functools import reduce

# Original list
fruits = ['apple', 'banana', 'pineapple', 'orange', 'grape', 'kiwi']
print("Original list:", fruits)

# Using iter() to iterate manually
fruit_iter = iter(fruits)
print("\nIterating manually with iter() and next():")
print(next(fruit_iter))  # first item
print(next(fruit_iter))  # second item

# Using map() to uppercase each fruit
upper_fruits = list(map(str.upper, fruits))
print("\nUppercase fruits (map()):", upper_fruits)

# Using filter() to select fruits with names longer than 5 letters
long_fruits = list(filter(lambda f: len(f) > 5, fruits))
print("Fruits with names longer than 5 letters (filter()):", long_fruits)

# Using reduce() to concatenate all fruit names into one string
all_fruits_str = reduce(lambda x, y: x + ", " + y, fruits)
print("All fruits concatenated (reduce()):", all_fruits_str)

# Using reduce() to find the longest fruit name
longest_fruit = reduce(lambda x, y: x if len(x) > len(y) else y, fruits)
print("Longest fruit name (reduce()):", longest_fruit)

# Using enumerate() to get index and value
print("\nEnumerating fruits (enumerate()):")
for index, fruit in enumerate(fruits):
    print(index, fruit)

# Enumerate starting at 1
print("\nEnumerating fruits starting at 1:")
for index, fruit in enumerate(fruits, start=1):
    print(index, fruit)

#  Using sorted() to create sorted versions without changing original
sorted_fruits = sorted(fruits)
print("\nAlphabetically sorted (sorted()):", sorted_fruits)

sorted_reverse = sorted(fruits, reverse=True)
print("Reverse alphabetical sorted (sorted()):", sorted_reverse)

sorted_by_length = sorted(fruits, key=len)
print("Sorted by length (sorted()):", sorted_by_length)

# Combine sorted() with map()
upper_sorted = sorted(map(str.upper, fruits))
print("Uppercase then sorted:", upper_sorted)

# List slicing examples
print("\nLast 3 fruits (slicing):", fruits[-3:])
print("Every second fruit (slicing):", fruits[::2])
sub_fruits = fruits[1:4]
print("Sub-list fruits[1:4] (slicing):", sub_fruits)

# Reversing lists
fruits.reverse()
print("\nList reversed (reverse()):", fruits)

fruits.reverse()
print("List restored to original order (reverse()):", fruits)
