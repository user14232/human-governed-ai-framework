# Phase 2 Abschluss – Anti-Patterns, Failure Modes & bewusste Nicht-Ziele

**Status:** Framework-intern, normativ  
**Ziel:** Phase 2 (Governance & Trennung) explizit abschließen  
**Leser:** Humans, alle Framework-Rollen

---

## 1. Zweck dieses Dokuments

Dieses Dokument definiert **explizit**, welche Nutzungsarten, Erwartungen und
Verhaltensweisen **nicht zulässig**, **nicht unterstützt** oder **bewusst ausgeschlossen**
sind.

Es dient drei Zwecken:

1. Vermeidung impliziter Annahmen
2. Schutz vor schleichender Autonomisierung
3. Klare Abgrenzung von Phase 3+ Features

> **Prinzip:**  
> Ein Framework ist erst dann stabil, wenn es klar sagen kann,  
> **was es nicht tut – selbst wenn es könnte.**

---

## 2. Anti-Patterns (verbotene Nutzungsweisen)

Diese Anti-Patterns sind **konzeptionell verboten**, auch wenn sie technisch möglich wären.

### AP-01: „Der Agent weiß schon, was gemeint ist“

**Beschreibung:**  
Agenten interpretieren unvollständige, mehrdeutige oder implizite Anforderungen
ohne explizite Artefakte.

**Warum verboten:**

- zerstört Determinismus
- verschiebt Verantwortung vom Menschen zum System
- macht Entscheidungen nicht auditierbar

**Gegenmaßnahme:**

- fehlende Informationen → Stop
- Ambiguität → explizite Annahme im Artefakt oder Human Decision

---

### AP-02: Impliziter Fortschritt ohne Artefakt

**Beschreibung:**  
Ein Workflow-Schritt wird fortgesetzt, obwohl ein erforderliches Artefakt
oder eine Genehmigung fehlt.

**Warum verboten:**

- unterläuft Governance
- erzeugt „Phantom-Entscheidungen“
- bricht Audit-Trail

**Gegenmaßnahme:**

- harte Gates
- Orchestrator darf nur Präsenz + Entscheidung prüfen, nichts inferieren

---

### AP-03: „Friendly Agent“-Verhalten

**Beschreibung:**  
Ein Agent kompensiert fehlende Inputs durch Annahmen,
Heuristiken oder „Best Practices“.

**Warum verboten:**

- Agent wird zum impliziten Entscheider
- Entscheidungen sind nicht mehr lokalisierbar

**Gegenmaßnahme:**

- Agenten dürfen nur transformieren, nicht vervollständigen
- Unklarheit → explizit dokumentieren oder stoppen

---

### AP-04: Architekturänderung als Implementation Detail

**Beschreibung:**  
Architekturregeln werden „nebenbei“ durch Code, Tests oder Konfiguration geändert.

**Warum verboten:**

- Architektur driftet unsichtbar
- Review verliert Referenzpunkt

**Gegenmaßnahme:**

- einzige legale Änderung: `architecture_change_proposal.md`
- ohne Decision → kein Fortschritt

---

### AP-05: Automatisierte Entscheidungen ohne Human Record

**Beschreibung:**  
Tools, Skripte oder Agenten treffen Entscheidungen, die eigentlich
Human Gates sind.

**Warum verboten:**

- Governance wird simuliert, nicht gelebt
- Verantwortung ist nicht mehr zuordenbar

**Gegenmaßnahme:**

- alle Entscheidungen → `decision_log.yaml`
- keine impliziten Approvals

---

## 3. Failure Modes (erwartete, erlaubte Fehlzustände)

Failure ist **kein Fehler im Framework**, sondern ein **valider Zustand**.

### FM-01: INIT → FAILED (Missing Inputs)

**Bedeutung:**

- Projekt ist nicht startfähig
- Framework schützt sich selbst

**Erwartetes Verhalten:**

- kein Fallback
- kein „Best Guess“
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

- Änderung ist nicht akzeptabel

**Erwartetes Verhalten:**

- Workflow endet
- kein automatisches Retry
- neue Iteration nur via Orchestrator + neue Artefakte

---

### FM-04: Architekturkonflikt ohne Entscheidung

**Bedeutung:**

- Plan kollidiert mit Contract
- Entscheidung fehlt

**Erwartetes Verhalten:**

- Blockade
- explizite Proposal-Erstellung
- kein Workaround

---

## 4. Was dieses Framework bewusst NICHT kann

Diese Punkte sind **keine Lücken**, sondern **Design-Entscheidungen**.

### N-01: Keine autonome Zieldefinition

Das Framework:

- definiert keine Ziele
- priorisiert nichts selbst
- erkennt keine „Opportunitäten“

👉 Ziele kommen **immer** von Menschen.

---

### N-02: Keine implizite Optimierung

Das Framework:

- optimiert keine Pläne
- vereinfacht keine Architektur
- „verbessert“ nichts ohne Auftrag

👉 Verbesserung ist ein **eigener Prozess** (Improvement Cycle).

---

### N-03: Keine Selbstheilung

Das Framework:

- repariert keine Fehler
- korrigiert keine Artefakte
- „lernt“ nicht im Hintergrund

👉 Fehler werden **sichtbar gemacht**, nicht verborgen.

---

### N-04: Keine Projekt-Intelligenz

Das Framework:

- versteht keine Domain
- interpretiert keine Regeln
- bewertet keine fachliche Qualität

👉 Fachlichkeit ist **Projektverantwortung**.

---

### N-05: Keine implizite Skalierung

Mehr Projekte:

- erzeugen keine neuen Abkürzungen
- erzeugen keine Shared State Logik
- verändern das Framework nicht automatisch

👉 Skalierung erfolgt **explizit oder gar nicht**.

---

## 5. Phase-2-Abschlusskriterium (Definition of Done)

Phase 2 gilt als **abgeschlossen**, wenn:

- jedes Stoppen erklärbar ist
- jedes Weitergehen belegbar ist
- jedes „Nein“ ein Artefakt hat
- jedes „Warum nicht?“ auf dieses Dokument verweist

> **Wenn sich das Framework unbequem anfühlt,  
> aber fair – dann ist Phase 2 erreicht.**

---

## 6. Übergang zu Phase 3 (nicht automatisch)

Phase 3 darf **erst** beginnen, wenn:

- mindestens ein realer Run gescheitert ist
- mindestens ein menschlicher Entscheid bewusst verzögert wurde
- kein Anti-Pattern nur „theoretisch“ ist

Phase 3 beginnt **nicht** durch Features,  
sondern durch **bewiesene Stabilität unter Druck**.
