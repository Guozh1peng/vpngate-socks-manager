import csv
import requests
from pathlib import Path


def parse_vpngate_csv(text):
    lines = [line for line in text.splitlines() if line.strip()]
    header_index = next(
        index for index, line in enumerate(lines)
        if line.startswith('#HostName,')
    )

    header_line = lines[header_index].lstrip('#')
    data_lines = []

    for line in lines[header_index + 1:]:
        if line.startswith('*'):
            break
        data_lines.append(line)

    return header_line, data_lines

cookies = {
    'sid': 'FA38FFD094F5',
    'x-hng': 'lang=zh-CN&domain=www.vpngate.net',
}

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

response = requests.get('https://www.vpngate.net/api/iphone/', cookies=cookies, headers=headers)
response.raise_for_status()

header, rows = parse_vpngate_csv(response.text)

csv_path = Path(__file__).with_name('vpngate.csv')
with csv_path.open('w', newline='', encoding='utf-8-sig') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(next(csv.reader([header])))
    writer.writerows(csv.reader(rows))

print(f'CSV saved to: {csv_path}')

