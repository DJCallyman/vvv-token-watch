# Chart Visualization Improvements for Outlier Data

## Problem
The Venice API analytics dashboard was showing data where one model (mistral-31-24b) had significantly more usage than others:
- **Requests**: 233 (next nearest: 7) - 33x more
- **Tokens**: 1,671,098 (next nearest: 13,640) - 122x more

This outlier was "crushing" the visualization, making smaller models nearly invisible on linear-scale charts.

## Solution Implemented

### 1. **Logarithmic Scale for Bar Charts**
- **Automatic Detection**: Charts now automatically use log scale when max > 10x min value
- **Benefits**: 
  - Outliers (233 requests) are clearly visible
  - Small values (1-7 requests) remain readable
  - Grid lines added for better readability on log scale
  - All data points are proportionally visible

### 2. **Sorted Data Display**
- Models are now sorted by volume (descending)
- Makes it easy to identify which models consume the most resources
- Visual hierarchy from highest to lowest usage

### 3. **Smart Number Formatting**
- Large numbers use K/M suffixes for readability:
  - `1,671,098` → `1.67M`
  - `13,640` → `13.6K`
  - `500` → `500`
- Prevents label overlap and improves chart cleanliness

### 4. **Enhanced Color Gradient**
- Switched from random colors to a green gradient
- Darker green = higher usage, lighter green = lower usage
- Provides visual hierarchy that reinforces the sorted order

### 5. **Improved Cost Chart**
- Pie chart now sorted by cost (descending)
- Shows both percentage AND dollar amounts in labels
- Total cost displayed in title
- Legend includes: Model name, cost, and percentage
- Smart label display: only shows percentages > 1% to avoid clutter

## Technical Details

### Usage Chart Changes
```python
# Before: Linear scale, unsorted
ax.bar(models, requests, ...)

# After: Log scale, sorted, formatted
sorted_indices = sorted(range(len(requests)), key=lambda i: requests[i], reverse=True)
ax.bar(short_models, requests, ...)
ax.set_yscale('log')  # If max > 10x min
ax.grid(True, which='both', axis='y', linestyle='--', alpha=0.3)
```

### Number Formatting
```python
if height >= 1000000:
    label = f'{height/1000000:.2f}M'
elif height >= 1000:
    label = f'{height/1000:.1f}K'
else:
    label = f'{int(height)}'
```

### Cost Chart Enhancement
```python
def make_autopct(values):
    def my_autopct(pct):
        total = sum(values)
        val = pct * total / 100.0
        if pct > 5:
            return f'{pct:.1f}%\n${val:.4f}'
        elif pct > 1:
            return f'{pct:.1f}%'
        else:
            return ''  # Too small to label
    return my_autopct
```

## Results

### Before
- Only mistral-31-24b was visible (tall bar crushing others)
- Other models appeared as flat lines near zero
- No way to compare smaller models
- Cost distribution unclear

### After
- ✅ **All models clearly visible** with log scale
- ✅ **Proportional comparison** possible across all scales
- ✅ **Sorted order** shows hierarchy instantly
- ✅ **Smart formatting** prevents clutter (1.67M vs 1,671,098)
- ✅ **Color gradient** reinforces visual hierarchy
- ✅ **Cost breakdown** shows percentages AND dollar amounts

## Files Modified
- `model_comparison.py`:
  - `render_usage_chart()` - Added log scale detection, sorting, and formatting
  - `render_cost_chart()` - Added sorting, enhanced labeling, percentage display

## Testing
Created test visualization with actual outlier data:
```bash
python -c "..." # Generated /tmp/test_log_charts.png
```
Confirmed:
- Log scale properly displays 233 and 1 on same chart
- Labels readable: "233", "7", "3", "2", "1"
- Token formatting works: "1.67M", "13.6K", "5.0K", "2.0K", "500"
- No matplotlib warnings or errors

## Future Enhancements
Consider adding:
1. Toggle between linear/log scale
2. Customizable threshold for auto-log scale
3. Hover tooltips showing exact values
4. Export functionality for chart data
5. Time-series comparison to show usage trends
