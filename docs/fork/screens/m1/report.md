# UI check: m1

Base: http://127.0.0.1:8000

| route | viewport | strict | problems | small tap targets |
|---|---|---|---|---|
| login | mobile |  | OK | 4 |
| start | mobile |  | OK | 3 |
| recipe-view | mobile |  | 1 JS error(s): ResponseError: Response returned an error code; 1 console error(s): Failed to load resource: the server responded with a status of 403 (Forbidden) | 15 |
| recipe-edit | mobile |  | OK | 11 |
| food-list | mobile |  | OK | 7 |
| shopping | mobile |  | OK | 3 |
| mealplan | mobile |  | OK | 5 |
| pantry | mobile |  | OK | 10 |
| settings | mobile |  | 1 console error(s): TypeError: Cannot read properties of undefined (reading 'id')
    at http://127.0.0.1:8000/static/vue3/assets/AccountSettings-D6GtDIl8.js:1:2185
    at http://127.0.0.1:8000/static/vue3/assets/vue.esm-bundler-CqD-zRSx.js:3:46119
    at $n (http://127.0.0.1:8000/static/vue3/assets/vue.esm-bundler-CqD | 10 |
| login | small |  | OK | 4 |
| start | small |  | OK | 3 |
| recipe-view | small |  | 1 JS error(s): ResponseError: Response returned an error code; 1 console error(s): Failed to load resource: the server responded with a status of 403 (Forbidden) | 15 |
| recipe-edit | small |  | OK | 11 |
| food-list | small |  | OK | 7 |
| shopping | small |  | OK | 3 |
| mealplan | small |  | OK | 5 |
| pantry | small |  | OK | 10 |
| settings | small |  | 1 console error(s): TypeError: Cannot read properties of undefined (reading 'id')
    at http://127.0.0.1:8000/static/vue3/assets/AccountSettings-D6GtDIl8.js:1:2185
    at http://127.0.0.1:8000/static/vue3/assets/vue.esm-bundler-CqD-zRSx.js:3:46119
    at $n (http://127.0.0.1:8000/static/vue3/assets/vue.esm-bundler-CqD | 10 |
| login | desktop |  | OK | 0 |
| start | desktop |  | OK | 0 |
| recipe-view | desktop |  | 1 JS error(s): ResponseError: Response returned an error code; 1 console error(s): Failed to load resource: the server responded with a status of 403 (Forbidden) | 0 |
| recipe-edit | desktop |  | OK | 0 |
| food-list | desktop |  | OK | 0 |
| shopping | desktop |  | OK | 0 |
| mealplan | desktop |  | 1 JS error(s): ResponseError: Response returned an error code; 1 console error(s): Failed to load resource: the server responded with a status of 403 (Forbidden) | 0 |
| pantry | desktop |  | OK | 0 |
| settings | desktop |  | OK | 0 |

RESULT: OK
