places = ["Kyoto", "Reykjavik", "Cape Town", "Buenos Aires", "Vancouver"]

# Print the list in its original order
print("Original list:")
print(places)

# Print again to show it's still in original order
print("\nStill original order:")
print(places)

# Use reverse() to reverse the list order
places.reverse()
print("\nList after reverse():")
print(places)

# Use reverse() again to restore original order
places.reverse()
print("\nList after reversing again (back to original):")
print(places)

# Use sort() to sort list in alphabetical order
places.sort()
print("\nList after sort() (alphabetical):")
print(places)

# Use sort() with reverse=True for reverse alphabetical order
places.sort(reverse=True)
print("\nList after sort(reverse=True) (reverse alphabetical):")
print(places)
