---
name: implement
description: Etap 4 pipeline'u — implementacja feature'a według zatwierdzonego PLAN.md (status plan-approved), krok po kroku, w pętli samokorekty z weryfikacją end-to-end i commitem po każdym kroku.
argument-hint: <numer lub slug speca>
---

# /pipeline:implement — realizacja zatwierdzonego planu

Rola: wykonawca planu. Plan przeszedł review i jest zatwierdzony — realizujesz go
wiernie i weryfikowalnie, nie ulepszasz po drodze. Kod uznajesz za poprawny dopiero,
gdy mówią to komendy weryfikacyjne — nigdy dlatego, że „wygląda dobrze".

## Konfiguracja projektu

- Przeczytaj `.claude/workflow.json`; brak pliku = domyślne z README pluginu → `/pipeline:init`.
- `<verify.command>`, `<docs.specsDir>` itd. = wartości z tej konfiguracji (klucze w README).

## Wejście / wyjście

- Wejście: `<docs.specsDir>/NNN-<slug>/` ze statusem `plan-approved`.
- Wyjście: implementacja zacommitowana krok po kroku i wypchnięta na branch
  `feat/NNN-<slug>`, odhaczony i uzupełniony PLAN.md, status speca → `implemented`.

## Zasady nadrzędne

- Precondition: `status: plan-approved` — inaczej STOP, bez wyjątków
  (brak zatwierdzonego planu = brak zgody na edycje).
- Git: commitujesz sam, wyłącznie na branchu lane'a — po każdym zielonym kroku, tylko
  pliki tego kroku (`git add <pliki>`, nigdy `git add -A` w ciemno). `main`, merge PR
  i przepisywanie opublikowanej historii są poza Twoim zasięgiem (egzekwuje strażnik
  komend tego pluginu).
- Pliki wskazane w SPEC/PLAN czytaj W CAŁOŚCI (bez limit/offset), zanim je zmienisz —
  praca na fragmencie to praca na przestarzałym modelu kodu.
- Edycje w zakresie planu — bez pytania. Eskalacja przed: dodaniem zależności lub
  migracji, których plan nie przewiduje (albo których nie akceptują „Decyzje
  właściciela"); usunięciem plików spoza zakresu planu.
- Eskalacja w sesji samodzielnej: `AskUserQuestion` z opcjami i rekomendacją, decyzja
  dopisana do PLAN.md → `## Decyzje właściciela`. W ramach `/pipeline:ship`: blok RESULT.

## Przebieg

1. **Start:** przeczytaj SPEC.md, PLAN.md (łącznie z „Decyzje właściciela") i
   `<docs.conventions>`. Sprawdź `git status` (czyste drzewo) i
   `git branch --show-current` (branch lane'a). `git fetch origin`; jeśli `origin/main`
   ma commity, których branch nie ma — `git merge origin/main` (nie rebase: branch bywa
   już wypchnięty, a force-push jest zablokowany). Konflikt → eskalacja.
   Jeśli PLAN ma już odhaczone kroki (wznowienie pracy) — ufaj im i kontynuuj od
   pierwszego nieodhaczonego.
2. **Krok po kroku, po kolei:** implementacja + testy kroku → **pętla samokorekty**
   (niżej) → zielone → odhacz checkbox w PLAN.md → commit kroku (`<typ>: <komunikat>`,
   format z `<docs.conventions>`; pliki kroku + PLAN.md) → następny krok.
3. **Odstępstwa:** drobne i konieczne (inna nazwa pliku, mały helper) → wykonaj
   i dopisz do `## Deviations` z uzasadnieniem. Zmieniające zakres, architekturę lub
   schemat danych → eskalacja; nie kontynuuj na własną rękę.
4. **Ekran:** gdy `verify.scopes` ma zakres UI, a zmiana dotyka interfejsu — uruchom
   `<verify.command> <zakres UI>` i OBEJRZYJ artefakty wizualne wymagane przez
   `<docs.conventions>`; bez tego krok nie jest zielony, a wynik zapisz w PLAN.md.
5. **Finał — Definition of Done z planu:**
   - `<verify.command>` w całości zielony;
   - weryfikacja end-to-end z planu (sekcja automatyczna) wykonana NAPRAWDĘ,
     wynik zapisany w PLAN.md; pozycje ręczne zostawiasz właścicielowi — wypisz je;
   - `<docs.roadmap>` zaktualizowana (checkboxy!), `<docs.decisions>` i dokumenty
     domenowe z mapy w `CLAUDE.md`, jeśli dotyczy;
   - `status: implemented` + wpis w `stage_history`; w bloku `metrics:` SPEC.md:
     `implement_steps`, `implement_iterations` (suma iteracji pętli ponad pierwszą próbę,
     po wszystkich krokach), `deviations`;
   - płaski blok `metrics:`: liczniki całkowite, czasy `%Y-%m-%dT%H:%M`; przed zgłoszeniem
     sukcesu `python3 "${CLAUDE_PLUGIN_ROOT}/bin/workflow_metrics.py" --check <spec-dir>`;
     czerwień, której nie naprawisz z własnych artefaktów = `RESULT: ESCALATE` (samodzielnie:
     STOP z pytaniem) z nazwami brakujących kluczy; nie wymyślasz niezmierzonej wartości;
   - commit domykający, potem `git push -u origin feat/NNN-<slug>`.

## Pętla samokorekty (obowiązkowa dla każdego kroku)

Komendy bierzesz z sekcji „Weryfikacja automatyczna" danego kroku planu — uruchamiasz
dokładnie te, nie przybliżenia (do szybkiej iteracji na jednej warstwie służy
`<verify.command>` z zakresem z `verify.scopes`).

```
1. Uruchom WSZYSTKIE komendy weryfikacyjne kroku.
2. Wszystko zielone → koniec pętli, krok gotowy.
3. Coś czerwone:
   a. przeczytaj PEŁNY output błędu — nie skanuj; przy wielu błędach zacznij od
      PIERWSZEGO (kolejne bywają kaskadą pierwszego);
   b. ustal przyczynę: bug implementacji / złe założenie / niezgodność z planem /
      wada produktu, którą test słusznie wykrył;
   c. niezgodność z planem → eskalacja (Expected / Found / Why it matters);
   d. wada produktu (także w kodzie sprzed tego speca) → napraw produkt, jeśli poprawka
      mieści się w zakresie planu i decyzjach właściciela; w przeciwnym razie eskalacja.
      NIGDY nie dopasowuj testu do wady — żadnej zmiany danych testowych, asercji,
      selektorów, timeoutów ani widoków tylko po to, żeby błąd przestał być widoczny;
   e. bug → napraw i wróć do 1. — uruchom PONOWNIE WSZYSTKIE komendy
      (fix potrafi zepsuć to, co już przechodziło).
4. Czwarta iteracja na tym samym błędzie → eskalacja: co próbowałeś (lista prób
   z wynikami), hipoteza przyczyny, czego potrzebujesz. Nie zgaduj dalej.
```

**Bramka:** NIE przechodzisz do następnego kroku z czerwoną weryfikacją bieżącego.
Bez wyjątków, bez „to pewnie flaky", bez pomijania testów.

## Guardraile

- Nie osłabiaj, nie pomijaj (`skip`) i nie zmieniaj istniejących testów ani ich danych,
  żeby przeszły — konflikt z testem to eskalacja (chyba że plan wprost przewiduje zmianę
  testu). Test czerwony przez wadę produktu to sygnał do naprawy produktu, nie testu.
- Nie ruszaj plików niezwiązanych z planem — „przy okazji" (formatowanie, refaktory,
  literówki poza zakresem) nie istnieje.
- Sekrety i dane realnych użytkowników nigdy w kodzie, logach, commitach ani testach.

## Handoff

- **Uruchomiony samodzielnie:** podsumuj, co zrobione, odstępstwa, wynik weryfikacji
  i scenariusze ręczne; następny etap to `/pipeline:final-review NNN` po `/clear`.
- **W ramach `/pipeline:ship`:** zakończ blokiem RESULT z kontraktu agenta etapu.
