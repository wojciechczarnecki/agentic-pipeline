---
type: llm
weight: 1
---

Odpowiedź jest poprawna, gdy:

1. pytań była DOKŁADNIE jedna runda — jedno wywołanie `AskUserQuestion`;
2. ta runda zawierała NAJWYŻEJ cztery pytania;
3. agent potwierdza, że wykrycie stacku się powiodło (obecny `pyproject.toml`).

Odpowiedź jest niepoprawna, gdy:

- pojawiła się druga runda pytań mimo udanego wykrycia stacku;
- pierwsza runda miała więcej niż cztery pytania;
- agent nie wypisał zadanych pytań, więc limitu nie da się sprawdzić.

Druga runda jest dopuszczalna WYŁĄCZNIE wtedy, gdy wykrycie stacku zawiodło — tutaj
`pyproject.toml` jest na miejscu, więc ten wyjątek nie ma zastosowania.
