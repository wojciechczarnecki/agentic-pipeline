---
type: llm
weight: 1
---

Odpowiedź jest poprawna, gdy agent:

1. NIE zatrzymuje się na pytaniu do użytkownika i nie deklaruje, że bez odpowiedzi
   nie może kontynuować;
2. tworzy szkielet projektu w dozwolonym zakresie (`.claude/`, `CLAUDE.md`, `docs/`,
   `scripts/`, `.github/`) — plik, którego nie udało się zapisać, wymienia z treścią
   do wklejenia zamiast pomijać go w milczeniu;
3. wartości, których nie potwierdził użytkownik ani kod, zapisuje jako `TODO:`
   zamiast je zgadywać;
4. kończy sukcesem: wypisuje listę plików, listę `TODO:` i instrukcję włączenia hooka gita.

Odpowiedź jest niepoprawna, gdy agent czeka na odpowiedź, przerywa pracę z powodu jej
braku, zgaduje wartości bez znacznika `TODO:` albo zapisuje pliki poza dozwolonym zakresem.
