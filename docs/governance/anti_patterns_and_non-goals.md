# Phase 2 Abschluss â€“ Anti-Patterns, Failure Modes & bewusste Nicht-Ziele

**Status:** DevOS-intern, normativ  
**Ziel:** Phase 2 (Governance & Trennung) explizit abschlieÃŸen  
**Leser:** Humans, alle DevOS-Rollen

---

## 1. Zweck dieses Dokuments

Dieses Dokument definiert **explizit**, welche Nutzungsarten, Erwartungen und
Verhaltensweisen **nicht zulÃ¤ssig**, **nicht unterstÃ¼tzt** oder **bewusst ausgeschlossen**
sind.

Es dient drei Zwecken:

1. Vermeidung impliziter Annahmen
2. Schutz vor schleichender Autonomisierung
3. Klare Abgrenzung von Phase 3+ Features

> **Prinzip:**  
> Ein Framework ist erst dann stabil, wenn es klar sagen kann,  
> **was es nicht tut â€“ selbst wenn es kÃ¶nnte.**

---

## 2. Anti-Patterns (verbotene Nutzungsweisen)

Diese Anti-Patterns sind **konzeptionell verboten**, auch wenn sie technisch mÃ¶glich wÃ¤ren.

### AP-01: â€žDer Agent weiÃŸ schon, was gemeint istâ€œ

**Beschreibung:**  
Agenten interpretieren unvollstÃ¤ndige, mehrdeutige oder implizite Anforderungen
ohne explizite Artefakte.

**Warum verboten:**

- zerstÃ¶rt Determinismus
- verschiebt Verantwortung vom Menschen zum System
- macht Entscheidungen nicht auditierbar

**GegenmaÃŸnahme:**

- fehlende Informationen â†’ Stop
- AmbiguitÃ¤t â†’ explizite Annahme im Artefakt oder Human Decision

---

### AP-02: Impliziter Fortschritt ohne Artefakt

**Beschreibung:**  
Ein Workflow-Schritt wird fortgesetzt, obwohl ein erforderliches Artefakt
oder eine Genehmigung fehlt.

**Warum verboten:**

- unterlÃ¤uft Governance
- erzeugt â€žPhantom-Entscheidungenâ€œ
- bricht Audit-Trail

**GegenmaÃŸnahme:**

- harte Gates
- Orchestrator darf nur PrÃ¤senz + Entscheidung prÃ¼fen, nichts inferieren

---

### AP-03: â€žFriendly Agentâ€œ-Verhalten

**Beschreibung:**  
Ein Agent kompensiert fehlende Inputs durch Annahmen,
Heuristiken oder â€žBest Practicesâ€œ.

**Warum verboten:**

- Agent wird zum impliziten Entscheider
- Entscheidungen sind nicht mehr lokalisierbar

**GegenmaÃŸnahme:**

- Agenten dÃ¼rfen nur transformieren, nicht vervollstÃ¤ndigen
- Unklarheit â†’ explizit dokumentieren oder stoppen

---

### AP-04: ArchitekturÃ¤nderung als Implementation Detail

**Beschreibung:**  
Architekturregeln werden â€žnebenbeiâ€œ durch Code, Tests oder Konfiguration geÃ¤ndert.

**Warum verboten:**

- Architektur driftet unsichtbar
- Review verliert Referenzpunkt

**GegenmaÃŸnahme:**

- einzige legale Ã„nderung: `architecture_change_proposal.md`
- ohne Decision â†’ kein Fortschritt

---

### AP-05: Automatisierte Entscheidungen ohne Human Record

**Beschreibung:**  
Tools, Skripte oder Agenten treffen Entscheidungen, die eigentlich
Human Gates sind.

**Warum verboten:**

- Governance wird simuliert, nicht gelebt
- Verantwortung ist nicht mehr zuordenbar

**GegenmaÃŸnahme:**

- alle Entscheidungen â†’ `decision_log.yaml`
- keine impliziten Approvals

---

## 3. Failure Modes (erwartete, erlaubte FehlzustÃ¤nde)

Failure ist **kein Fehler im DevOS-System**, sondern ein **valider Zustand**.

### FM-01: INIT â†’ FAILED (Missing Inputs)

**Bedeutung:**

- Projekt ist nicht startfÃ¤hig
- Framework schÃ¼tzt sich selbst

**Erwartetes Verhalten:**

- kein Fallback
- kein â€žBest Guessâ€œ
- klarer Abbruch

---

### FM-02: Plan existiert, aber keine Freigabe

**Bedeutung:**

- Mensch hat noch nicht entschieden

**Erwartetes Verhalten:**

- Stillstand
- keine Eskalation
- kein Zeitdruck durch System

---

### FM-03: Review = FAILED

**Bedeutung:**

- Ã„nderung ist nicht akzeptabel

**Erwartetes Verhalten:**

- Workflow endet (terminaler Zustand)
- kein automatisches Retry
- neue Iteration nur via Orchestrator + neue `run_id` + neue Artefakte (siehe `contracts/runtime_contract.md` Abschnitt 8.1)

---

### FM-04: Architekturkonflikt ohne Entscheidung

**Bedeutung:**

- Plan kollidiert mit Contract
- Entscheidung fehlt

**Erwartetes Verhalten:**

- `agent_architecture_guardian` produziert `arch_review_record.md` mit outcome `CHANGE_REQUIRED`
- Blockade bei `ARCH_CHECK`
- `architecture_change_proposal.md` wird produziert und muss explizit genehmigt werden
- kein Workaround
- nach Genehmigung: neue Version `arch_review_record.md` mit outcome `PASS` erforderlich

---

### FM-05: Reject oder Defer bei Approval-Gate

**Bedeutung:**

- Mensch hat Artefakt abgelehnt oder zurÃ¼ckgestellt

**Erwartetes Verhalten:**

- Workflow ist blockiert am aktuellen Gate
- Bei `reject`: neue Version des Artefakts produzieren, neue Genehmigung einholen
- Bei `defer`: Stillstand bis explizite Entscheidung vorliegt
- kein automatisches Eskalieren
- Versionierung gemÃ¤ÃŸ `contracts/runtime_contract.md` Abschnitt 3

---

## 4. Was DevOS bewusst NICHT kann

Diese Punkte sind **keine LÃ¼cken**, sondern **Design-Entscheidungen**.

### N-01: Keine autonome Zieldefinition

Das Framework:

- definiert keine Ziele
- priorisiert nichts selbst
- erkennt keine â€žOpportunitÃ¤tenâ€œ

ðŸ‘‰ Ziele kommen **immer** von Menschen.

---

### N-02: Keine implizite Optimierung

Das Framework:

- optimiert keine PlÃ¤ne
- vereinfacht keine Architektur
- â€žverbessertâ€œ nichts ohne Auftrag

ðŸ‘‰ Verbesserung ist ein **eigener Prozess** (Improvement Cycle).

---

### N-03: Keine Selbstheilung

Das Framework:

- repariert keine Fehler
- korrigiert keine Artefakte
- â€žlerntâ€œ nicht im Hintergrund

ðŸ‘‰ Fehler werden **sichtbar gemacht**, nicht verborgen.

---

### N-04: Keine Projekt-Intelligenz

Das Framework:

- versteht keine Domain
- interpretiert keine Regeln
- bewertet keine fachliche QualitÃ¤t

ðŸ‘‰ Fachlichkeit ist **Projektverantwortung**.

---

### N-05: Keine implizite Skalierung

Mehr Projekte:

- erzeugen keine neuen AbkÃ¼rzungen
- erzeugen keine Shared State Logik
- verÃ¤ndern das Framework nicht automatisch

ðŸ‘‰ Skalierung erfolgt **explizit oder gar nicht**.

---

## 5. Phase-2-Abschlusskriterium (Definition of Done)

Phase 2 gilt als **abgeschlossen**, wenn:

- jedes Stoppen erklÃ¤rbar ist
- jedes Weitergehen belegbar ist
- jedes â€žNeinâ€œ ein Artefakt hat
- jedes â€žWarum nicht?â€œ auf dieses Dokument verweist

> **Wenn sich das Framework unbequem anfÃ¼hlt,  
> aber fair â€“ dann ist Phase 2 erreicht.**

---

## 6. Ãœbergang zu Phase 3 (nicht automatisch)

Phase 3 darf **erst** beginnen, wenn:

- mindestens ein realer Run gescheitert ist
- mindestens ein menschlicher Entscheid bewusst verzÃ¶gert wurde
- kein Anti-Pattern nur â€žtheoretischâ€œ ist

Phase 3 beginnt **nicht** durch Features,  
sondern durch **bewiesene StabilitÃ¤t unter Druck**.
