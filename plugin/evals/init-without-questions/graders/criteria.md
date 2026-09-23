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
   zamiast je zgadywać — z jednym wyjątkiem: `language` bez wskazania w argumencie to
   `"en"` bez znacznika `TODO:`, bo `en` jest wartością domyślną;
4. kończy sukcesem: wypisuje listę plików, listę `TODO:` i instrukcję włączenia hooka gita;
5. generuje `CLAUDE.md` i pliki w `docs/` po angielsku (pokazane pierwsze linie są
   angielskie, np. tytuł `# Roadmap`, kolumna backlogu `Priority`) i ustawia `language`
   na `"en"` — język tego polecenia nie wskazuje języka dokumentów.

Odpowiedź jest niepoprawna, gdy agent czeka na odpowiedź, przerywa pracę z powodu jej
braku, zgaduje wartości bez znacznika `TODO:`, zapisuje pliki poza dozwolonym zakresem,
generuje dokumenty po polsku, ustawia `language` na `"pl"` albo zostawia przy `language`
znacznik `TODO`.

Przebieg ewaluacyjny blokuje zapis w `.claude/` niezależnie od reguł uprawnień, więc brak
`.claude/settings.json` i `.claude/workflow.json` jest ograniczeniem środowiska, a NIE
zachowaniem skilla. Wymienienie ich z treścią do wklejenia spełnia punkt 2 w całości
i nie wolno z tego powodu uznać odpowiedzi za niepoprawną.
