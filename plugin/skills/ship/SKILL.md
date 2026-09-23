---
name: ship
description: Orkestrator pipeline'u — prowadzi feature od SPEC (status spec-ready lub późniejszy) do otwartego PR, uruchamiając etapy jako subagenty ze świeżym kontekstem; właściciel wchodzi tylko przy eskalacji i przy decyzjach po końcowym review.
argument-hint: <numer lub slug speca>
---

# /pipeline:ship — od SPEC do PR

Rola: koordynator, nie wykonawca. NIE planujesz, NIE implementujesz i NIE recenzujesz sam —
każdy etap robi osobny subagent ze świeżym kontekstem (daje to samo, co nowa sesja po
`/clear`). Twój kontekst ma zostać lekki: czytasz frontmatter SPEC.md, „Streszczenie dla
właściciela" (`## Owner summary`) z PLAN.md i bloki RESULT od subagentów — nie diff, nie
kod.

## Konfiguracja projektu

- Przeczytaj `.claude/workflow.json`; brak pliku = domyślne z README pluginu → `/pipeline:init`.
- `<verify.command>`, `<docs.specsDir>` itd. = wartości z tej konfiguracji (klucze w README).

## Język

- Pliki, które zapisujesz w repozytorium (SPEC, PLAN — każda sekcja, także wpisy decyzji,
  review log, deviations i raport końcowego review), oraz treść PR piszesz w języku
  z `language` w `.claude/workflow.json`; brak klucza albo wartość spoza `en`/`pl` = `en`.
  Sekcję wskazujesz oboma nagłówkami i przyjmujesz którykolwiek (mapa sekcji — sekcja
  „Mapa sekcji").
- Zawsze po angielsku, niezależnie od `language` i sesji: komunikaty commitów, tytuły PR,
  nazwy branchy i slugi speców, klucze bloku `RESULT`, klucze metryk i tokeny wag.
- Rozmowa z właścicielem — pytania, eskalacje, podsumowania i handoff — w języku sesji
  Claude Code, nigdy według `language`.

## Mapa sekcji

- Zanim poszukasz sekcji w SPEC albo PLAN, wczytaj narzędziem `Read` mapę sekcji
  `${CLAUDE_PLUGIN_ROOT}/templates/sections.md` (klucz → nagłówek polski → angielski).
  Sekcję wskazujesz oboma nagłówkami i przyjmujesz którykolwiek.
- Nieudany odczyt mapy albo szablonu kończy etap — nie zgadujesz nagłówków i nie
  odtwarzasz szablonu z pamięci. Pod `/pipeline:ship`: `RESULT: ESCALATE`; uruchomiony
  samodzielnie: STOP z tym samym komunikatem do właściciela. Komunikat podaje ścieżkę
  pliku i regułę do dopisania w `permissions.allow` (`.claude/settings.json` projektu
  albo ustawień użytkownika): `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)`,
  a dla klonu z `--plugin-dir` — `Read(//<ścieżka katalogu pluginu bez początkowego />/**)`;
  `<marketplace>` odczytujesz z rozwiniętej ścieżki `${CLAUDE_PLUGIN_ROOT}`
  (`…/plugins/cache/<marketplace>/pipeline/<wersja>`); gdy strażnik pokazał już
  ostrzeżenie z gotową regułą, podajesz tę regułę.

## Stan

Źródłem prawdy jest `status:` w SPEC.md, nie ta rozmowa. `/pipeline:ship` przerwany
w dowolnym miejscu wznawia się od bieżącego statusu — także dla speców rozpoczętych
ręcznie etap po etapie.

| Status          | Agent           | Tryb     | Wynik DONE                              |
|-----------------|-----------------|----------|-----------------------------------------|
| `spec-ready`    | `planner`       | —        | `plan-draft`                            |
| `plan-draft`    | `plan-reviewer` | —        | `plan-approved` (sam, gdy brak eskalacji) |
| `plan-approved` | `implementer`   | —        | `implemented`                           |
| `implemented`   | `reviewer`      | `report` | raport znalezisk → **bramka właściciela** |
| `implemented` + decyzje zapisane | `reviewer` | `apply` | PR z zielonym CI + `done` |
| `done`          | —               | —        | STOP: nic do zrobienia (podaj link PR, jeśli istnieje) |

Status `spec-draft` lub brak SPEC → STOP: najpierw `/pipeline:idea`.

## Start

1. Ustal spec (argument; bez argumentu wylistuj `<docs.specsDir>/*/SPEC.md` ze statusem
   od `spec-ready` do `implemented` i zapytaj, który brać).
2. `git status` czysty. Branch lane'a `feat/NNN-<slug>`: istnieje → `git switch` na niego;
   nie istnieje → `git switch main && git pull --ff-only && git switch -c feat/NNN-<slug>`.
   Przy pracy równoległej sesja działa już w worktree lane'a — nie przełączaj branchy.
3. Brak `metrics.started_at` w SPEC → dopisz (`date +%Y-%m-%dT%H:%M`) razem z
   `escalations: 0` i zacommituj. Płaski blok `metrics:` trzyma liczniki jako liczby
   całkowite, a znaczniki czasu w formacie `%Y-%m-%dT%H:%M`. Licznik ma istnieć od startu,
   żeby zestawienie metryk pokazywało `0`, a nie `-` (brak pomiaru).

## Uruchamianie agenta etapu

Narzędzie `Agent` z typem agenta z tabeli. Agenci pochodzą z tego pluginu, więc w sesji
widoczni są pod nazwami z przedrostkiem: `pipeline:planner`, `pipeline:plan-reviewer`,
`pipeline:implementer`, `pipeline:reviewer` — używaj tych nazw jako `subagent_type`.
Jeśli sesja nie zna nazwy z przedrostkiem, użyj samej nazwy agenta (`planner` itd.).

Prompt zawiera WYŁĄCZNIE: numer i ścieżkę speca, tryb (dla `reviewer`), katalog roboczy
oraz przypomnienie o kontrakcie niżej. Nie przekazuj historii tej rozmowy ani własnych
hipotez — świeży kontekst to element metody.

Na wynik agenta etapu czekasz, zanim pójdziesz dalej.

## Kontrakt agenta etapu

Obowiązuje każdego agenta uruchomionego przez `/pipeline:ship`:

- Realizujesz wczytany skill etapu. Nie możesz pytać właściciela (`AskUserQuestion` jest
  niedostępne). Wszędzie, gdzie skill każe zapytać, poczekać albo zrobić STOP — kończysz
  pracę blokiem `RESULT: ESCALATE`.
- Decyzje właściciela z SPEC.md i PLAN.md → `## Decyzje właściciela` (`## Owner decisions`)
  są wiążące; nie eskaluj ponownie kwestii już rozstrzygniętej.
- Stan zapisujesz w plikach speca i w commitach, nigdy tylko w odpowiedzi.
- Język: pliki speca i treść PR w `language`; commity, tytuł PR i klucze bloku RESULT
  po angielsku; treść ESCALATION i SUMMARY orkiestrator pokazuje właścicielowi w języku
  sesji.
- Metryki etapu wpisujesz sam do płaskiego bloku `metrics:` we frontmatterze SPEC.md:
  liczniki to liczby całkowite, znaczniki czasu `%Y-%m-%dT%H:%M`, `escalations` od startu.
  Licznik `escalations` zwiększa wyłącznie orkiestrator — agent etapu go nie zmienia.
- Odpowiedź końcowa zaczyna się od bloku:

```
RESULT: DONE | ESCALATE
STATUS: <status speca po etapie>
METRICS: <klucz=wartość; …>
ESCALATION: <tylko przy ESCALATE — problem; opcje (≤ 4); rekomendacja; dlaczego>
SUMMARY: <≤ 10 linii; dla reviewer/report — tabela znalezisk: id | waga | jedno zdanie>
```

## Protokół wyniku

- Brak bloku RESULT albo `STATUS` niezgodny z plikiem → uruchom etap ponownie raz; drugi
  raz → eskaluj sam, opisując, co agent zwrócił.
- **ESCALATE** → `AskUserQuestion`: pytanie z `ESCALATION`, opcje od agenta, rekomendowana
  pierwsza z dopiskiem „(Recommended)" — zadane w języku sesji, niezależnie od języka,
  w którym agent je napisał. Odpowiedź (data, etap, pytanie, decyzja) dopisz w języku
  z `language` do PLAN.md → `## Decyzje właściciela` (`## Owner decisions`), a gdy PLAN.md
  jeszcze nie istnieje — do tej samej sekcji SPEC.md. Zwiększ `metrics.escalations`,
  zacommituj (`docs: record owner decision for NNN`) i uruchom NOWEGO agenta tego samego etapu.
- Ten sam etap eskaluje po raz trzeci → STOP. Opisz właścicielowi sytuację i poproś
  o przejęcie sterowania.

## Wyzwalacze eskalacji (wiążące dla wszystkich agentów)

- nowa zależność albo podbicie wersji major istniejącej,
- migracja danych (sekcja `migrations` konfiguracji),
- luka lub sprzeczność w SPEC,
- blocker z recenzji planu, którego recenzent nie umie naprawić w samym planie,
- odstępstwo od planu zmieniające zakres, architekturę albo schemat danych,
- pętla samokorekty wyczerpana (4. iteracja na tym samym błędzie),
- test wykrywa wadę produktu, której naprawa wykracza poza zakres planu lub decyzje
  właściciela — zamiast obchodzić ją zmianą testu albo danych testowych,
- konflikt przy `git merge origin/main`.

## Bramka: końcowe review

1. `reviewer` w trybie `report` → raport w PLAN.md → `## Final review`.
2. Pokaż właścicielowi tabelę znalezisk z SUMMARY i zadaj `AskUserQuestion` — oba
   w języku sesji, tokeny wag bez tłumaczenia:
   „Przyjmij `blocker` i `worth-fixing`, odrzuć `nit` (Recommended)" / „Przyjmij
   wszystkie" / „Wybiorę pojedynczo" / „Tylko `blocker`". Przy „Wybiorę pojedynczo" poproś
   o listę id.
3. Decyzje (przyjęte i odrzucone id) zapisz w `## Decyzje właściciela`
   (`## Owner decisions`) w języku z `language`, zacommituj.
4. `reviewer` w trybie `apply` → poprawki, push, PR, zielone CI, dopiero wtedy `done`.

Brak znalezisk w raporcie → bramkę pomiń: zapisz w decyzjach, w języku z `language`, że
znalezisk nie było, i przejdź do `apply`.

## Zamknięcie

1. Z RESULT `reviewer/apply` weź link PR, status CI i link do artefaktów wizualnych
   z przebiegu CI.
2. `PushNotification`: „PR NNN gotowy do merge: <tytuł>" — tylko przy zielonym CI. PR
   z czerwonym CI nie dostaje tego powiadomienia; reviewer zwraca wtedy ESCALATE, który
   prowadzisz przez „Protokół wyniku".
3. Zielone CI z testem zaliczonym dopiero po retry (flaky) → sprawdź, że reviewer dopisał
   go do `<docs.backlog>`; jeśli nie, uruchom `reviewer` (tryb `apply`)
   ponownie z tym zadaniem. Sam nie edytujesz plików speca ani dokumentów.
4. Podsumowanie dla właściciela: link PR, status CI, link do artefaktów wizualnych, ręczne
   scenariusze do sprawdzenia przed merge'em (z PLAN.md → „Weryfikacja end-to-end →
   Ręczna" / `### Manual (performed by the owner)` w `## End-to-end verification`),
   metryki speca.

## Guardraile

- Nigdy nie mergujesz PR — to bramka właściciela (egzekwuje też strażnik komend tego
  pluginu).
- Nie pomijasz etapów i nie wykonujesz pracy etapu we własnym kontekście, nawet „drobnej".
- Nie ustawiasz statusów speca za agentów — robią to etapy; Ty tylko czytasz.
