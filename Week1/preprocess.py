import os
import pandas as pd

df = pd.read_csv('Reviews.csv')

# Take the top 10% of the data
top_n = max(1, int(len(df) * 0.1))
df_top_10_percent = df.iloc[:top_n].copy()

# Save to the same path as the original file
input_path = 'Reviews.csv'
base_dir = os.path.dirname(os.path.abspath(input_path))
base_name = os.path.splitext(os.path.basename(input_path))[0]
output_path = os.path.join(base_dir, f"{base_name}_top10percent.csv")
df_top_10_percent.to_csv(output_path, index=False)

print(f"Saved: {output_path}")
print(f"Original row count: {len(df)}, Saved row count:{len(df_top_10_percent)}")