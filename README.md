Use Python 3.8 - 3.12 (3.13 not supporting)

Usage:
1. ```pip install -r requirements.txt```
2. Before run You can change destination address(It's affect to search engine results)<br />
Now selected: "DEST": -1257786, # г Москва, ул Никольская д. 7-9, стр. 4<br />
If you want change your destination.<br />
Open www.wildberries.ru web browser and open development tool "Inspect Request & Response".<br />
Select your destination in website and follow: `200 GET https://user-geo-data.wildberries.ru/get-geo-info?currency=RUB&lati...` request.<br />
Open "Response tab" and find. `"xinfo": "appType=1&curr=rub&dest=-1257786&hide_dtype=13&spp=30"` in JSON.<br />
`...dest=-1257786...`
Your current destination is -1257786<br />
Change "DEST" value in `main.py`:
```
...
PARAMS: Dict = {
    "URL_OR_ID": None,
    "SCAN_DESCRIPTION": False,
    "MODEL": None,
    "PATH": 'data',
    # Необходимо указать DEST(Пункт выдачи. Для поиска). Найти можно в консоле. OPTIONS | search.wb.ru
    "DEST": -1257786, # г Москва, ул Никольская д. 7-9, стр. 4
    "DEBUG": True, # Print stages
}
...
```

```python main.py```
3. Insert Wildberries link or article number and press enter.<br />
Examples:
```
Загружаем конфигурации...
Конфигурации не найдены! Создаём первую конфигурацию...
[CONFIG] Введите ссылку на карточку Wildberries:
https://www.wildberries.ru/catalog/161308460/detail.aspx 
```
or
```
Загружаем конфигурации...
Конфигурации не найдены! Создаём первую конфигурацию...
[CONFIG] Введите ссылку на карточку Wildberries:
161308460
```
4. If you want scan description field in card, enter y and press Enter
```
[CONFIG] Сканировать описание?
Yes/No: y
```
5. Select NLP model or ChatGPT. Type number and press Enter<br />
When selected All it will use all NLP without ChatGPT.
6. Wait for results. You will get table.<br />
The table was sorted by best matches.<br />
Result example:
```
                                PARSING RESULT                                 
 URL      https://www.wildberries.ru/catalog/161308460/detail.aspx 
 Article  161308460                                                
                                  Parsed Data                                  
┌──────────────────────┬───────────────┬──────────────┬──────┬───────┬────────┐
│                      │    Search     │   Per Page   │      │       │        │
│ Query                │   Position    │   Position   │ Page │ Pages │  Hits  │
├──────────────────────┼───────────────┼──────────────┼──────┼───────┼────────┤
│ Игровой компьютер    │      19       │      19      │  1   │  439  │ 43884  │
│ RTX 4060 8GB         │      199      │      99      │  2   │   8   │  723   │
│ 32GB DDR4 3000MHz    │      255      │      55      │  3   │   4   │  312   │
│ Intel Core i5 12400F │      457      │      57      │  5   │  17   │  1625  │
│ гарантия 3 года      │       0       │      0       │  0   │ 1178  │ 117706 │
│ Windows 10 Pro       │       0       │      0       │  0   │  60   │  5943  │
│ NVMe SSD             │       0       │      0       │  0   │  33   │  3259  │
│ белый корпус         │       0       │      0       │  0   │  21   │  2002  │
│ мощная видеокарта    │       0       │      0       │  0   │   8   │  744   │
│ 960GB SSD M.2        │       0       │      0       │  0   │   3   │  291   │
│                      │       0       │      0       │  0   │   0   │   0    │
└──────────────────────┴───────────────┴──────────────┴──────┴───────┴────────┘

Process finished with exit code 0
```