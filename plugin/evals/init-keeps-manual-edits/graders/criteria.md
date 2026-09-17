---
type: llm
weight: 1
---

Odpowiedź jest poprawna, gdy po drugim uruchomieniu:

1. sekcja `## Zasada domowa` w `CLAUDE.md` i dopisany wiersz w rejestrze decyzji są
   NIETKNIĘTE — dokładnie w tej treści, którą wpisał użytkownik;
2. drugie uruchomienie nie zapisało plików, których nie dotyczyły nowe odpowiedzi —
   `git status --porcelain` po drugim przebiegu nie pokazuje dla nich nowych zmian;
3. agent mówi wprost, które pliki utworzył, które zaktualizował, a które pominął.

Odpowiedź jest niepoprawna, gdy ręcznie dopisana treść zniknęła albo została nadpisana
szablonem, gdy drugi przebieg przepisał pliki bez powodu, albo gdy agent tego nie sprawdził.
