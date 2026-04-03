import requests
import pandas as pd

# Отримати максимум дозволених даних (API дозволяє до 1000 записів)
url = 'https://api.alternative.me/fng/?limit=1000&format=json'

response = requests.get(url)
data = response.json()

# Обробка
fgi_data = data['data']
fgi_df = pd.DataFrame(fgi_data)
fgi_df['datetime'] = pd.to_datetime(fgi_df['timestamp'], unit='s')
fgi_df = fgi_df.rename(columns={
    'value': 'fgi',
    'value_classification': 'classification'
})
fgi_df['fgi'] = fgi_df['fgi'].astype(int)
fgi_df = fgi_df[['datetime', 'fgi', 'classification']]
fgi_df = fgi_df.sort_values('datetime')

# Вивід кількості днів
print(f"Кількість записів: {len(fgi_df)}")
print(fgi_df.head())

# Зберегти у файл
fgi_df.to_csv('fear_greed_index_full.csv', index=False)
