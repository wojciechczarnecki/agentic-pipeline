---
name: plan-review
description: Etap 3 pipeline'u — adwersaryjny review PLAN.md (status plan-draft) świeżym okiem; poprawia plan w miejscu i sam ustawia plan-approved, chyba że trafi na wyzwalacz eskalacji.
argument-hint: <numer lub slug speca>
---

# /pipeline:plan-review — krytyka, poprawa i zatwierdzenie planu

Rola: recenzent, którego zadaniem jest ZNALEZIENIE problemów, zanim staną się kodem.
Wyjdź z założenia, że plan ma luki — Twoim sukcesem jest ich wskazanie, nie
przyklepanie planu. Po recenzji to Ty decydujesz, czy plan jest gotowy do implementacji —
właściciel wchodzi tylko wtedy, gdy decyzja nie należy do Ciebie (krok 5).

## Konfiguracja projektu

- Przeczytaj `.claude/workflow.json`; brak pliku = domyślne z README pluginu → `/pipeline:init`.
- `<verify.command>`, `<docs.specsDir>` itd. = wartości z tej konfiguracji (klucze w README).

## Język

- Pliki, które zapisujesz w repozytorium (SPEC, PLAN — każda sekcja, także wpisy decyzji,
  review log, deviations i raport końcowego review), oraz treść PR piszesz w języku
  z `language` w `.claude/workflow.json`; brak klucza albo wartość spoza `en`/`pl` = `en`.
  Sekcję wskazujesz oboma nagłówkami i przyjmujesz którykolwiek (mapa sekcji w README
  pluginu).
- Zawsze po angielsku, niezależnie od `language` i sesji: komunikaty commitów, tytuły PR,
  nazwy branchy i slugi speców, klucze bloku `RESULT`, klucze metryk i tokeny wag.
- Rozmowa z właścicielem — pytania, eskalacje, podsumowania i handoff — w języku sesji
  Claude Code, nigdy według `language`.

## Wejście / wyjście

- Wejście: `<docs.specsDir>/NNN-<slug>/PLAN.md` + SPEC.md ze statusem `plan-draft`.
- Wyjście: poprawiony PLAN.md z sekcją `## Review log`; status speca → `plan-approved`
  albo eskalacja; zmiany zacommitowane.

## Kroki

1. **Znajdź spec**; precondition `status: plan-draft` (inaczej STOP i wyjaśnij).
2. **Anty-anchoring:** najpierw przeczytaj SAM SPEC (bez otwierania planu) i zanotuj
   3–5 punktów, jak sam byś to ugryzł. Dopiero potem otwórz PLAN.md i porównaj —
   rozbieżności to pierwsze tropy.
3. **Przejdź checklistę** (każdy punkt zakończ werdyktem OK / problem + co z tym):
   - **pokrycie:** każde AC ze SPEC ma kroki i test dowodzący; macierz zgadza się z listą kroków;
   - **zgodność:** `<docs.conventions>` (wzorce kodu, teksty dla użytkownika, testy)
     i `<docs.decisions>` (plan nie łamie decyzji);
   - **minimalność:** czy istnieje prostsza droga; czy pominięto coś reużywalnego z kodu; czy zakres nie wykracza poza SPEC;
   - **wykonalność:** kolejność kroków bez zależności „w przód", migracje uwzględnione,
     ryzyka nieprzemilczane (różnice bazy testowej i produkcyjnej, strefy czasowe,
     autoryzacja, długości pól);
   - **weryfikacja E2E:** rozdzielona na automatyczną (agent) i ręczną (właściciel);
     część automatyczna realna do wykonania na uruchomionej aplikacji; do ręcznej nie
     trafia nic, co da się zautomatyzować. Gdy `verify.scopes` ma zakres UI, a zmiana
     dotyka interfejsu — wymagaj `<verify.command> <zakres UI>` oraz artefaktów wizualnych
     i scenariusza przeglądowego wymaganych przez `<docs.conventions>`.
   - **testowalność:** każdy krok ma sekcję „Weryfikacja automatyczna"
     (`Automatic verification:`) z DOKŁADNYMI komendami (ścieżki testów), które
     `/pipeline:implement` uruchomi w pętli samokorekty — nie ogólnik „dodaj testy";
   - **streszczenie:** „Streszczenie dla właściciela" (`## Owner summary`) zgodne z planem
     — zwłaszcza flagi nowej zależności i migracji danych;
   - **język:** PLAN (każda sekcja, także Review log) w bieżącym `language`; niezgodność
     poprawiasz w miejscu (tłumaczysz plan, SPEC-a nie ruszasz) — waga `major`.
   Każdy problem ma wagę — token pisany jako kod w każdym języku: `blocker` (plan
   doprowadzi do złego wyniku albo nie pokrywa AC), `major` (istotna luka poprawialna
   w planie), `minor`.
4. **Wprowadź poprawki bezpośrednio w PLAN.md.** W `## Review log` zapisz: datę,
   znaleziska z wagą, co zmieniono i dlaczego, oraz co sprawdzono i uznano za poprawne
   (żeby kolejne etapy nie powtarzały tej pracy).
5. **Decyzja o zatwierdzeniu.** Eskaluj (NIE ustawiaj `plan-approved`), gdy:
   - został blocker, którego nie umiesz naprawić w samym planie;
   - problem leży w SPEC (luka, sprzeczność, AC niemożliwe do pokrycia) — SPEC nie
     poprawiasz;
   - plan wprowadza nową zależność (lub podbicie major) albo migrację danych, a SPEC/PLAN →
     „Decyzje właściciela" (`## Owner decisions`) jej nie akceptuje.
   W pozostałych przypadkach ustaw sam `status: plan-approved` + wpis w `stage_history`,
   a w Review log jednym zdaniem uzasadnij, dlaczego plan jest gotowy.
   Eskalacja w sesji samodzielnej: `AskUserQuestion` z opcjami i rekomendacją (pierwsza,
   „(Recommended)"), decyzja dopisana do PLAN.md → `## Decyzje właściciela`
   (`## Owner decisions`), potem
   dokończ krok 5.
6. **Zamknięcie etapu:** w bloku `metrics:` SPEC.md ustaw `plan_review_blockers`,
   `plan_review_majors` (liczone przed poprawkami) i `plan_changes` (liczba zmian
   wprowadzonych w planie).
   Płaski blok `metrics:`: liczniki całkowite, czasy `%Y-%m-%dT%H:%M`; przed zgłoszeniem
   sukcesu `workflow_metrics.py --check <spec-dir>`.
   Czerwień, której nie naprawisz z własnych artefaktów = `RESULT: ESCALATE` (samodzielnie:
   STOP z pytaniem) z nazwami brakujących kluczy; nie wymyślasz wartości, której nie zmierzyłeś.
   Zacommituj (`docs: review PLAN NNN <slug>`).

## WAŻNE — konsekwencja statusu

`plan-approved` uruchamia regułę zgód: od tej chwili `/pipeline:implement` edytuje
pliki w zakresie planu bez pytania. Dlatego wyzwalacze eskalacji z kroku 5 są bezwzględne —
nie zatwierdzaj planu z niezaakceptowaną zależnością lub migracją, nawet jeśli wydaje się
oczywista.

## Guardraile

- Nie poprawiaj SPEC — problem w SPEC to eskalacja; za zgodą właściciela status może
  wrócić do `spec-draft`.
- Nie przepisuj planu od zera dla stylu — poprawiaj to, co ma znaczenie.
- Znaleziska formułuj konkretnie: „krok 3 nie pokrywa AC2, bo …", nie „plan mógłby być lepszy".

## Handoff

- **Uruchomiony samodzielnie:** podsumuj znaleziska i zmiany; następny etap to
  `/pipeline:implement NNN` po `/clear`.
- **W ramach `/pipeline:ship`:** zakończ blokiem RESULT z kontraktu agenta etapu.
