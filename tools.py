def longest_consecutive_sequence(nums):
    if not nums:
        return []

    nums_set = set(nums)
    longest_sequence = []
    current_sequence = []

    for num in nums:
        if num - 1 not in nums_set:  # Start of a new sequence
            current_sequence = [num]
            current_num = num + 1

            while current_num in nums_set:
                current_sequence.append(current_num)
                current_num += 1

            # Update the longest sequence if needed
            if len(current_sequence) > len(longest_sequence):
                longest_sequence = current_sequence

    return longest_sequence[-5:]

# Exemple d'utilisation
numbers = [100, 4, 200, 1, 3, 2, 5, 6, 7]
result = longest_consecutive_sequence(numbers)
print("La plus longue séquence de nombres consécutifs est :", result)