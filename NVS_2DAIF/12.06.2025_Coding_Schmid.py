# 11. Container with Most Water

class Solution(object):
    def maxArea(self, height):
        left = 0
        right = len(height) - 1
        max_water = 0 
        step = 1

        print(f"Input array: {height}")

        while left < right: 
            width = right - left
            current_height = min(height[left], height[right])
            current_area = width * current_height
            
            max_water = max(max_water, current_area)

            if height[left] < height[right]:
                left += 1
            else: 
                right -= 1
            step += 1
        
        return max_water

solution = Solution()

result1 = solution.maxArea([1,8,6,2,5,4,8,3,7])
print(f"Result: {result1}\n")