// German public site copy. Publishes all 25 approved routes.
export default {
  code: "de",
  htmlLang: "de",
  dir: "ltr",
  prefix: "de/",
  label: "Deutsch",
  nav: {
    home: "Startseite",
    platform: "Plattform",
    features: "Funktionen",
    solutions: "Lösungen",
    pricing: "Preise",
    resources: "Ressourcen",
    documentation: "Dokumentation",
    help: "Hilfe",
    about: "Über uns",
    contact: "Kontakt",
    faq: "FAQ",
    integrations: "Integrationen",
    security: "Sicherheit",
    "get-started": "Erste Schritte",
    privacy: "Datenschutz",
    terms: "Bedingungen",
  },
  footer: {
    tagline: "© 2026 CUBI Platform · Planen. Steuern. Klüger bauen.",
    groups: [
      { title: "Produkt", links: [["features", "Funktionen"], ["platform", "Plattform"], ["pricing", "Preise"]] },
      { title: "Lernen", links: [["documentation", "Dokumentation"], ["resources", "Ressourcen"]] },
      { title: "Unternehmen", links: [["about", "Über uns"], ["contact", "Kontakt"]] },
    ],
  },
  cta: { label: "CUBI-Arbeitsbereich öffnen", href: "/app/" },
  pages: [
    {
      id: "home",
      path: "",
      title: "CUBI | Bauplanung und Projektsteuerung an einem Ort",
      description: "CUBI verbindet Terminplanung, Projektsteuerung, Ressourcen, Kosten und Dokumente in einem Arbeitsbereich für Bauprojekte.",
      eyebrow: "CUBI PLATTFORM",
      h1: "Planung und Steuerung, verbunden.",
      lead: "Ein Arbeitsbereich für Bauprojekte: den Plan organisieren, die Lieferung verfolgen und Projektinformationen näher an die Entscheidung bringen.",
      sections: [
        {
          h2: "Was CUBI verbindet",
          p: "Alle Funktionen lesen denselben Projekt-, Kalender- und Aktivitätsdatensatz.",
          cards: [
            { h3: "Planung & Terminplanung", p: "Arbeitsstruktur, Aktivitäten, Kalender, Beziehungen und Basislinie in einem Workflow." },
            { h3: "Projektsteuerung", p: "Meilensteine, Status und Kennzahlen aus demselben Plan, den das Team ausführt." },
            { h3: "Ressourcen & Kosten", p: "Bedarf, Zuweisungen und Kosten sichtbar bei der Aktivität, zu der sie gehören." },
          ],
        },
      ],
      cta: { title: "Bringen Sie Ihr Projekt in den Fokus.", text: "Prüfen Sie den verbundenen Arbeitsablauf im CUBI-Arbeitsbereich.", label: "Arbeitsbereich öffnen", href: "/app/" },
    },
    {
      id: "platform",
      path: "platform/",
      title: "CUBI Plattform | Bauprojekt-Steuerung",
      description: "Die CUBI Plattform verbindet Planung, Steuerung, Ressourcen, Kosten, Dokumente und KI-Unterstützung in einem Arbeitsbereich.",
      eyebrow: "CUBI PLATTFORM",
      h1: "Eine verbundene Steuerungsplattform",
      lead: "Öffentliche Seiten informieren über das Produkt; Projektdaten liegen ausschließlich im authentifizierten Arbeitsbereich.",
      sections: [
        {
          h2: "Ein Projekt, ein Datensatz",
          p: "Jede Funktion arbeitet auf demselben Projekt und denselben Berechtigungen.",
          cards: [
            { h3: "Terminplanung", p: "Struktur, Aktivitäten, Kalender und Abhängigkeiten explizit und nachvollziehbar." },
            { h3: "Steuerung", p: "Status, Meilensteine und Kennzahlen ohne parallele Tabellenkalkulation." },
            { h3: "Zugriff", p: "Umgebung und Aktionen folgen den Rollen, die der Server prüft." },
          ],
        },
      ],
      cta: { title: "Sehen Sie die Plattform", text: "Öffnen Sie den Arbeitsbereich mit Ihrem Konto.", label: "Arbeitsbereich öffnen", href: "/app/" },
    },
    {
      id: "features",
      path: "features/",
      title: "CUBI Funktionen | Planung, Steuerung, Kosten und KI",
      description: "Wie CUBI Planung, Projektsteuerung, Ressourcen, Kosten, Dokumente, Risiken, Berichte und KI-Unterstützung verbindet.",
      eyebrow: "CUBI FUNKTIONEN",
      h1: "Jede Funktion mit der Arbeit verbunden",
      lead: "Verfügbarkeit hängt von der Umgebung ab, für die Ihr Konto berechtigt ist.",
      sections: [
        {
          h2: "Planen und steuern",
          p: "Ein gemeinsamer Datensatz bedeutet, dass eine Planänderung dort sichtbar wird, wo sie zählt.",
          cards: [
            { h3: "Planung & Terminplanung", p: "Arbeitsstruktur, Aktivitäten, Kalender, Beziehungen, Basislinie und Fortschritt." },
            { h3: "Projektsteuerung", p: "Meilensteine, Status und Kennzahlen in einer konsistenten Sicht." },
            { h3: "Dokumente, Risiken, Berichte", p: "Nachweise bleiben bei der Aktivität, die sie erklären." },
          ],
        },
      ],
      cta: { title: "Funktionen im Detail", text: "Jede Funktion hat eine eigene Seite mit ihrem Umfang.", label: "Terminplanung ansehen", href: "/de/features/" },
    },
    {
      id: "solutions",
      path: "solutions/",
      title: "CUBI Lösungen | Projektabwicklung im Bauwesen",
      description: "CUBI für Auftragnehmer, Bauherren und Steuerungsteams, die Plan und Nachweise zusammenführen wollen.",
      eyebrow: "LÖSUNGEN",
      h1: "Für Teams, die den Plan ausführen",
      lead: "Bauprojekte scheitern selten an fehlenden Daten, sondern an getrennten Daten. CUBI führt sie zusammen.",
      sections: [
        {
          h2: "Rollen im Projekt",
          p: "Jede Rolle sieht den Ausschnitt, den sie für ihre Entscheidung braucht.",
          cards: [
            { h3: "Auftragnehmer", p: "Terminplan, Fortschritt und Nachweise für die eigene Leistung." },
            { h3: "Bauherr", p: "Status und Meilensteine gegenüber dem vereinbarten Basisplan." },
            { h3: "Steuerung", p: "Kennzahlen und Abweichungen aus derselben Datenbasis." },
          ],
        },
      ],
      cta: { title: "Ihr Szenario", text: "Sprechen Sie mit uns über Ihr Projekt.", label: "Kontakt", href: "/de/contact/" },
    },
    {
      id: "pricing",
      path: "pricing/",
      title: "CUBI Preise | Pro-Abonnement",
      description: "CUBI Pro wird in Monatseinheiten erworben. Der Server bestätigt den Anspruch nach einer verifizierten Zahlung.",
      eyebrow: "PREISE",
      h1: "Klare Abrechnung",
      lead: "Zwölf Monate bedeuten zwölf Monatseinheiten, kein separates Jahresangebot. Ohne konfigurierten Anbieter wird nichts berechnet.",
      sections: [
        {
          h2: "So funktioniert der Kauf",
          p: "Sie wählen die Monate, prüfen die Summe und gehen zur Kasse. Die Seite selbst berechnet nichts.",
          cards: [
            { h3: "Monatseinheiten", p: "Jede Einheit ist ein Monat; sie werden gemeinsam erworben." },
            { h3: "Bestehendes Abonnement", p: "Ein bestätigter Kauf verlängert das bestehende Ablaufdatum." },
            { h3: "Kein Anbieter, keine Zahlung", p: "Ist kein verifizierter Anbieter konfiguriert, startet keine Zahlung." },
          ],
        },
      ],
      cta: { title: "Pro erwerben", text: "Die Kasse läuft auf der englischen Seite.", label: "Zur Kasse", href: "/pricing/" },
    },
    {
      id: "resources",
      path: "resources/",
      title: "CUBI Ressourcen | Produktübersicht und Leitfäden",
      description: "Leitfäden und Referenzen zu Umgebungen, Projektaufbau, Terminplanung, Steuerung und Datenzugriff.",
      eyebrow: "RESSOURCEN",
      h1: "Material für die tägliche Arbeit",
      lead: "Die Ressourcen folgen dem Produkt und nennen die Umgebung, für die sie gelten.",
      sections: [
        {
          h2: "Einstieg und Referenz",
          p: "Wählen Sie den Leitfaden, der zu Ihrer Rolle passt.",
          cards: [
            { h3: "Erste Schritte", p: "Anmelden, Umgebung wählen und ein autorisiertes Projekt öffnen." },
            { h3: "Engineering-Umgebung", p: "Planung, Terminplanung, Steuerung und Berichte." },
            { h3: "Enterprise-Umgebung", p: "Organisationsweite Rollen und Aufgaben für berechtigte Konten." },
          ],
        },
      ],
      cta: { title: "Dokumentation", text: "Die vollständigen Leitfäden stehen bereit.", label: "Dokumentation öffnen", href: "/de/documentation/" },
    },
    {
      id: "documentation",
      path: "documentation/",
      title: "CUBI Dokumentation | Leitfäden für Plattform und Arbeitsbereich",
      description: "Leitfäden zu Umgebungen, Projektaufbau, Terminplanung, Steuerung und Datenzugriff in CUBI.",
      eyebrow: "DOKUMENTATION",
      h1: "Dokumentation für Ihre Arbeit",
      lead: "Jeder Leitfaden nennt die Umgebung, für die er gilt.",
      sections: [
        {
          h2: "Wählen Sie Ihren Einstieg",
          p: "Rolle und Umgebung bestimmen den passenden Leitfaden.",
          cards: [
            { h3: "Erste Schritte", p: "Anmelden, Umgebung wählen, autorisiertes Projekt öffnen." },
            { h3: "Daten und API", p: "Wie Projektdaten begrenzt, versioniert und gelesen werden." },
            { h3: "Sicherheit", p: "Identität, Sitzungen, Rollen und Projektmitgliedschaft zusammen." },
          ],
        },
      ],
      cta: { title: "Hilfe nötig?", text: "Das Help Center beantwortet die häufigen Fälle.", label: "Zum Help Center", href: "/help/" },
    },
    {
      id: "contact",
      path: "contact/",
      title: "Kontakt zu CUBI | Konto und Produktinformationen",
      description: "Kontakt für Kontozugang, Produktfragen und Projektszenarien.",
      eyebrow: "KONTAKT",
      h1: "Sprechen Sie mit uns",
      lead: "Für Kontozugang nennen Sie die Kontoadresse; für Projektszenarien die Projektgröße und die gewünschte Umgebung.",
      sections: [
        {
          h2: "Was wir brauchen",
          p: "Je genauer die Angaben, desto schneller die Antwort.",
          cards: [
            { h3: "Kontozugang", p: "Konto-E-Mail und die Umgebung, die geöffnet werden soll." },
            { h3: "Projektfrage", p: "Projektgröße, Rollen und der Bereich, der betroffen ist." },
            { h3: "Sicherheit", p: "Melden Sie vermutete Sicherheitsprobleme umgehend." },
          ],
        },
      ],
      cta: { title: "Schneller Einstieg", text: "Anmelden und die autorisierte Umgebung öffnen.", label: "Anmelden", href: "/login?next=/environments/" },
    },
    {
      id: "features-scheduling",
      path: "features/scheduling/",
      title: "CUBI Terminplanung | Arbeitsstruktur, Aktivitäten und Kalender",
      description:
        "Arbeitsstruktur, Aktivitäten, Kalender, Beziehungen, Basislinien und Fortschritt in einem terminplanzentrierten Bauablauf aufbauen.",
      eyebrow: "FUNKTIONEN · TERMINPLANUNG",
      h1: "Ein Terminplan, dem das Team vertraut",
      lead:
        "Planen Sie von der Arbeitsstruktur bis zur Aktivität, halten Sie Kalender und Beziehungen explizit und vergleichen Sie den Fortschritt mit einer gespeicherten Basislinie.",
      sections: [
        {
          h2: "Struktur vor Detail",
          p: "Arbeitsstruktur, Aktivitäten und Beziehungen teilen einen Projektdatensatz; Struktur und Detail laufen nicht auseinander.",
          cards: [
            { h3: "Arbeitsstruktur", p: "Ergebnisse und Arbeitspakete in einer Hierarchie, durch die das Team navigiert." },
            { h3: "Aktivitäten und Beziehungen", p: "Aktivitäten mit Dauer, Kalendern und Abhängigkeiten, die den tatsächlichen Ablauf abbilden." },
            { h3: "Kalender und Arbeitszeit", p: "Arbeitstage, Feiertage und Schichtmuster explizit halten, damit Termine aus echter Arbeitszeit berechnet werden." },
          ],
        },
        {
          h2: "Basislinien und Fortschritt",
          p: "Speichern Sie eine Basislinie vor Arbeitsbeginn und erfassen Sie den Fortschritt dagegen, statt die Historie zu ändern.",
          cards: [
            { h3: "Basislinien", p: "Den freigegebenen Plan unverändert halten und mit aktuellen Terminen und Dauern vergleichen." },
            { h3: "Fortschritt und Status", p: "Tatsächliche Starts und Enden erfassen, damit der Status widerspiegelt, was geschehen ist." },
            { h3: "Layouts und Ansichten", p: "Spalten, Gruppierung und Layout je Rolle speichern, ohne die Daten zu ändern." },
          ],
        },
      ],
      cta: { title: "Terminplanung prüfen", text: "Öffnen Sie den Arbeitsbereich mit Ihrem Konto.", label: "Arbeitsbereich öffnen", href: "/app/" },
    },
    {
      id: "features-project-controls",
      path: "features/project-controls/",
      title: "CUBI Projektsteuerung | Meilensteine, Status und Kennzahlen",
      description:
        "Meilensteine, Terminstatus, Kennzahlen und Entscheidungspunkte in einer konsistenten Betriebssicht zusammenführen.",
      eyebrow: "FUNKTIONEN · PROJEKTSTEUERUNG",
      h1: "Steuerung, die denselben Plan liest",
      lead:
        "Projektsteuerung wirkt nur, wenn sie den Plan misst, den das Team tatsächlich ausführt. CUBI hält Status, Meilensteine und Kennzahlen auf demselben Projektdatensatz.",
      sections: [
        {
          h2: "Eine Betriebssicht",
          p: "Meilensteine, Status und Kennzahlen werden aus dem Terminplan abgeleitet, nicht in einer parallelen Tabelle gepflegt.",
          cards: [
            { h3: "Meilensteine", p: "Vertragliche und interne Meilensteine gegen die Aktivitäten verfolgen, die sie treiben." },
            { h3: "Terminstatus", p: "Heute sehen, wo der Plan gegenüber der Basislinie steht – je Projekt und Arbeitspaket." },
            { h3: "Kennzahlen", p: "Kennzahlen auf denselben Terminen und demselben Fortschritt prüfen, die das Team erfasst." },
          ],
        },
        {
          h2: "Entscheidungen mit Nachweis",
          p: "Jeder Steuerungspunkt verweist auf die Aktivitäten, Dokumente und Datensätze, die ihn erklären.",
          cards: [
            { h3: "Entscheidungsprotokoll", p: "Die Begründung einer Termin- oder Kostenentscheidung beim geänderten Datensatz halten." },
            { h3: "Schwellen und Hinweise", p: "Relevante Schwellen definieren und anzeigen, bevor sie zur Überraschung werden." },
            { h3: "Berichte", p: "Berichte aus denselben Daten erzeugen, die der Arbeitsbereich nutzt – keine neu erfasste Kopie." },
          ],
        },
      ],
      cta: { title: "Steuerung ansehen", text: "Prüfen Sie Status und Meilensteine im Arbeitsbereich.", label: "Arbeitsbereich öffnen", href: "/app/" },
    },
    {
      id: "features-resources",
      path: "features/resources/",
      title: "CUBI Ressourcen | Ressourcenplanung und Zuweisungen",
      description:
        "Ressourcen, Rollen und Zuweisungen gegen echte Aktivitäten und Kalender planen, damit Bedarf und Verfügbarkeit sichtbar bleiben.",
      eyebrow: "FUNKTIONEN · RESSOURCEN",
      h1: "Ressourcenbedarf am Plan",
      lead:
        "Ressourcen, Rollen und Zuweisungen gehören zu den Aktivitäten, die sie brauchen; Bedarf und Verfügbarkeit stammen aus demselben Terminplan, den das Team ausführt.",
      sections: [
        {
          h2: "Von der Rolle zur Zuweisung",
          p: "Definieren Sie, was die Arbeit braucht, und weisen Sie es den Personen und Geräten zu, die sie liefern können.",
          cards: [
            { h3: "Ressourcen und Rollen", p: "Personen, Geräte und Rollen in einem Katalog, den alle Projekte teilen." },
            { h3: "Zuweisungen", p: "Ressourcen mit Menge und Dauer an Aktivitäten hängen, wie die Arbeit es verlangt." },
            { h3: "Verfügbarkeit", p: "Bedarf und Verfügbarkeit gemeinsam lesen statt zwei Systeme nachträglich abzugleichen." },
          ],
        },
        {
          h2: "Gegen die Realität planen",
          p: "Zuweisungsdaten folgen dem Aktivitätskalender; eine freigegebene Kalenderänderung aktualisiert den Bedarf.",
          cards: [
            { h3: "Kalenderbewusste Planung", p: "Ressourcenbedarf aus echter Arbeitszeit berechnen, nicht aus nominellen Tagen." },
            { h3: "Rollenabdeckung", p: "Überlastete Rollen sehen, bevor der Terminplan freigegeben wird." },
            { h3: "Verbindung zu Kosten", p: "Zuweisungen in die Kostensicht übernehmen, ohne zweite Dateneingabe." },
          ],
        },
      ],
      cta: { title: "Ressourcenbedarf prüfen", text: "Öffnen Sie den Arbeitsbereich mit Ihrem Konto.", label: "Arbeitsbereich öffnen", href: "/app/" },
    },
    {
      id: "features-cost",
      path: "features/cost/",
      title: "CUBI Kosten | Kostensicht verbunden mit Aktivitäten",
      description:
        "Ausgaben und Kostensicht mit den Aktivitäten, Ressourcen und dem Fortschritt verbinden, zu denen sie gehören – statt einer separaten Kostendatei.",
      eyebrow: "FUNKTIONEN · KOSTEN",
      h1: "Kosten, wo die Arbeit geschieht",
      lead:
        "Kosteninformationen nützen am meisten, wenn sie an der Aktivität hängen, die sie verursacht. CUBI hält Ausgaben und Kostendatensätze in ihrem Projekt.",
      sections: [
        {
          h2: "Ausgaben und Datensätze",
          p: "Erfassen Sie Ausgaben gegen das Arbeitselement, zu dem sie gehören, mit angehängtem Nachweis.",
          cards: [
            { h3: "Ausgaben", p: "Projektausgaben gegen Aktivitäten und Arbeitspakete mit klarem Prüfpfad erfassen." },
            { h3: "Kostensicht", p: "Kosten je Projekt, Aktivität und Arbeitspaket aus demselben Arbeitsbereich prüfen." },
            { h3: "Belege", p: "Das Dokument oder den Datensatz, der eine Kostenposition begründet, bei der Kostenposition halten." },
          ],
        },
        {
          h2: "Mit dem Fortschritt verbunden",
          p: "Kosten und Fortschritt werden gemeinsam gelesen, damit Earned-Value-Gespräche von konsistenten Daten starten.",
          cards: [
            { h3: "Fortschrittsbezug", p: "Ausgaben mit erfasstem Fortschritt vergleichen statt mit einem veralteten Prozentsatz." },
            { h3: "Währungsklarheit", p: "Währung und Arbeitspreis explizit erfassen, damit Summen nie geraten werden." },
            { h3: "Berichte", p: "Kosten aus Live-Projektdaten berichten, nicht aus einer monatlich neu erfassten Zusammenfassung." },
          ],
        },
      ],
      cta: { title: "Kostensicht prüfen", text: "Öffnen Sie den Arbeitsbereich mit Ihrem Konto.", label: "Arbeitsbereich öffnen", href: "/app/" },
    },
    {
      id: "features-documents",
      path: "features/documents/",
      title: "CUBI Dokumente | Projektakten und Verträge im Kontext",
      description:
        "Projektdokumente, Vertragsinformationen und Nachweise bei den Aktivitäten und Entscheidungen halten, die sie erklären.",
      eyebrow: "FUNKTIONEN · DOKUMENTE",
      h1: "Akten bei der Arbeit",
      lead:
        "Ein Dokument nützt, wenn es von der Aktivität aus gefunden wird, die es erklärt. CUBI hält Akten und Nachweise im Projektkontext.",
      sections: [
        {
          h2: "Eine Projektakte",
          p: "Dokumente und Verträge hängen am Projekt, Arbeitspaket oder an der Aktivität, zu der sie gehören.",
          cards: [
            { h3: "Projektdokumente", p: "Zeichnungen, Einreichungen und Akten speichern und finden, auf die ein Projekt angewiesen ist." },
            { h3: "Verträge", p: "Vertragsinformationen bei Termin- und Kostendatensätzen halten, die sie regeln." },
            { h3: "Nachweise", p: "Den Nachweis anhängen, der Fortschritt, Kosten oder eine Entscheidung stützt." },
          ],
        },
        {
          h2: "Auffindbar und nachvollziehbar",
          p: "Jede Akte behält Eigentümer und Historie, damit das Team weiß, was es vor sich hat.",
          cards: [
            { h3: "Eigentümerschaft", p: "Erfassen, wer ein Dokument wann hochgeladen hat, mit erhaltenem Projektbezug." },
            { h3: "Versionsbewusstsein", p: "Nicht auf einem überholten Dokument handeln, weil der Kontext sichtbar bleibt." },
            { h3: "Zugriffsgrenzen", p: "Dokumentzugriff folgt derselben Projektmitgliedschaft wie der restliche Arbeitsbereich." },
          ],
        },
      ],
      cta: { title: "Projektakten ansehen", text: "Öffnen Sie den Arbeitsbereich mit Ihrem Konto.", label: "Arbeitsbereich öffnen", href: "/app/" },
    },
    {
      id: "features-risks",
      path: "features/risks/",
      title: "CUBI Risiken | Risiken und Probleme am Plan",
      description:
        "Risiken und Probleme gegen die Aktivitäten, Termine und Verantwortlichen verfolgen, die sie betreffen – ohne separates Register.",
      eyebrow: "FUNKTIONEN · RISIKEN",
      h1: "Risiken an echten Terminen",
      lead:
        "Ein Risikoregister außerhalb des Terminplans kann nicht zeigen, was ein Risiko verzögern würde. CUBI hält Risiken und Probleme in der Projektakte.",
      sections: [
        {
          h2: "Register im Kontext",
          p: "Risiken und Probleme referenzieren die Aktivitäten und Meilensteine, die sie bedrohen; die Exposition wird dort sichtbar, wo sie zählt.",
          cards: [
            { h3: "Risikoregister", p: "Wahrscheinlichkeit, Auswirkung, Eigentümer und Maßnahme je Risiko erfassen." },
            { h3: "Probleme", p: "Bereits eingetretene Probleme mit der betroffenen Aktivität verfolgen." },
            { h3: "Eigentümerschaft", p: "Jedem Risiko und Problem einen benannten Eigentümer und ein Prüfdatum geben." },
          ],
        },
        {
          h2: "Von der Exposition zur Maßnahme",
          p: "Verknüpfen Sie eine Maßnahme mit dem geänderten Termin- oder Kostendatensatz, damit Minderung mehr als eine Notiz ist.",
          cards: [
            { h3: "Maßnahmen", p: "Die gewählte Maßnahme und die geänderten Aktivitäten erfassen." },
            { h3: "Schwellen", p: "Eskalieren, wenn die Exposition die definierte Schwelle überschreitet." },
            { h3: "Prüfhistorie", p: "Die Bewertungshistorie halten, damit eine Entscheidung später erklärbar ist." },
          ],
        },
      ],
      cta: { title: "Risikoregister prüfen", text: "Öffnen Sie den Arbeitsbereich mit Ihrem Konto.", label: "Arbeitsbereich öffnen", href: "/app/" },
    },
    {
      id: "features-reporting",
      path: "features/reporting/",
      title: "CUBI Berichte | Berichte aus Live-Projektdaten",
      description:
        "Projektberichte aus denselben Daten erzeugen, die der Arbeitsbereich nutzt – mit gespeicherten Layouts und einheitlichen Definitionen.",
      eyebrow: "FUNKTIONEN · BERICHTE",
      h1: "Eine Definition, viele Berichte",
      lead:
        "Berichte sind nur vergleichbar, wenn sie dieselben Definitionen teilen. CUBI erzeugt Berichte aus den Projektdaten, mit denen das Team täglich arbeitet.",
      sections: [
        {
          h2: "Bericht aus der Quelle",
          p: "Kein Export-und-Neuerfassen: Berichte lesen die Projektakte direkt.",
          cards: [
            { h3: "Gespeicherte Layouts", p: "Spalten, Gruppierung und Filter halten, die jede Zielgruppe erwartet." },
            { h3: "Terminberichte", p: "Termine, Fortschritt und Abweichung aus dem berechneten Terminplan berichten." },
            { h3: "Kosten- und Ressourcenberichte", p: "Kosten und Bedarf zusammen mit den Aktivitäten berichten, die sie erzeugt haben." },
          ],
        },
        {
          h2: "Konstruktiv konsistent",
          p: "Gemeinsame Definitionen sorgen dafür, dass zwei Berichte zur selben Sache nicht widersprechen.",
          cards: [
            { h3: "Gemeinsame Definitionen", p: "Eine Definition von Fortschritt und Abweichung über alle Berichte." },
            { h3: "Zeitraumbewusstsein", p: "Einen Zeitraum berichten und wissen, welche Datensätze damals gültig waren." },
            { h3: "Zielgruppensichten", p: "Jeder Zielgruppe die nötige Sicht geben, ohne Daten zu duplizieren." },
          ],
        },
      ],
      cta: { title: "Berichte ansehen", text: "Öffnen Sie den Arbeitsbereich mit Ihrem Konto.", label: "Arbeitsbereich öffnen", href: "/app/" },
    },
    {
      id: "features-ai-assistant",
      path: "features/ai-assistant/",
      title: "CUBI KI-Assistent | Projektbewusste Unterstützung",
      description:
        "Projektkontext nutzen, um Informationen zu ordnen, Zusammenfassungen vorzubereiten und nutzergeführte Projektabläufe mit einem sichtbaren Assistenten zu unterstützen.",
      eyebrow: "FUNKTIONEN · KI-UNTERSTÜTZUNG",
      h1: "Ein Assistent, der Ihren Projektkontext liest",
      lead:
        "Der CUBI-Assistent arbeitet mit dem Projekt, das Sie geöffnet haben. Er hilft beim Ordnen und Zusammenfassen; jede Entscheidung und jeder Schreibvorgang bleibt bei Ihnen.",
      sections: [
        {
          h2: "Unterstützung, nicht Autonomie",
          p: "Der Assistent schlägt vor und entwirft. Anlegen, Ändern oder Freigeben eines Projektdatensatzes bleibt eine Nutzeraktion.",
          cards: [
            { h3: "Projektkontext", p: "Antworten beruhen auf dem Projekt, für das die Sitzung berechtigt ist." },
            { h3: "Zusammenfassungen", p: "Lange Projektakten in eine prüfbare Zusammenfassung überführen." },
            { h3: "Navigationshilfe", p: "Das benötigte Fenster, den Datensatz oder die Definition finden, statt Menüs zu durchsuchen." },
          ],
        },
        {
          h2: "Sichtbar und begrenzt",
          p: "Der Assistent ist sichtbarer Teil des Arbeitsbereichs und an dieselben Berechtigungen gebunden wie der Nutzer.",
          cards: [
            { h3: "Gleiche Berechtigungen", p: "Der Assistent überschreitet nie den Zugriff des angemeldeten Nutzers." },
            { h3: "Transparente Aktionen", p: "Sie sehen den Vorschlag, bevor etwas geschrieben wird." },
            { h3: "Keine verdeckten Datenpfade", p: "Unterstützung nutzt die Projektdaten und Dienste, die das Produkt ohnehin bereitstellt." },
          ],
        },
      ],
      cta: { title: "Assistent ausprobieren", text: "Öffnen Sie den Arbeitsbereich mit Ihrem Konto.", label: "Arbeitsbereich öffnen", href: "/app/" },
    },
    {
      id: "integrations",
      path: "integrations/",
      title: "CUBI Integrationen | Projektdaten mit Ihren Systemen verbinden",
      description:
        "Verstehen, wie CUBI Projektdaten mit bestehenden Systemen einer Bauorganisation verbindet und was jede Integration voraussetzt.",
      eyebrow: "INTEGRATIONEN",
      h1: "Projektdaten, die mit Ihrer Organisation gehen",
      lead:
        "CUBI stellt Projektdaten über eine versionierte HTTP-API bereit und importiert und exportiert die Formate, die Projektteams austauschen. Jede Integration nennt, was sie braucht und was sie nicht tut.",
      sections: [
        {
          h2: "Wie Daten fließen",
          p: "Integrationen sind explizit: ein Kanal, ein Eigentümer, ein Umfang. Nichts wird still synchronisiert.",
          cards: [
            { h3: "HTTP-API", p: "Eine versionierte Projekt-API zum Lesen und Schreiben von Projektdatensätzen unter denselben Sitzungs- und Projektberechtigungen." },
            { h3: "Import und Export", p: "Terminpläne und Projektdaten in den Formaten austauschen, die Partner und Kunden erwarten." },
            { h3: "Dokumente und Nachweise", p: "Projektdokumente an ihre Datensätze hängen, damit der Nachweis mit den Daten reist." },
          ],
        },
        {
          h2: "Was eine Integration braucht",
          p: "Jede Verbindung ist auf einen Mandanten und ein Projekt begrenzt und wird wie jeder andere Client authentifiziert.",
          cards: [
            { h3: "Authentifizierung", p: "Sitzungs- und Anmeldedaten folgen denselben Identitätsregeln wie der Arbeitsbereich." },
            { h3: "Projektumfang", p: "Eine Verbindung sieht nur Projekte, für die ihr Konto berechtigt ist." },
            { h3: "Änderungskontrolle", p: "Versionierte Schreibvorgänge und Revisionsprüfungen schützen vor stillem Überschreiben." },
          ],
        },
      ],
      cta: { title: "Integration planen", text: "Sprechen Sie mit uns über Ihre Systeme.", label: "Kontakt", href: "/de/contact/" },
    },
    {
      id: "help",
      path: "help/",
      title: "CUBI Help Center | Antworten für den Arbeitsbereich",
      description:
        "Hilfe beim Anmelden, beim Wählen einer Umgebung, beim Öffnen eines Projekts und bei der Arbeit im CUBI-Arbeitsbereich.",
      eyebrow: "HELP CENTER",
      h1: "Hilfe, wenn die Arbeit weitergehen muss",
      lead:
        "Die meisten Fragen betreffen den Zugang: anmelden, die richtige Umgebung wählen und das richtige Projekt öffnen. Beginnen Sie hier und nutzen Sie dann die Hilfe im Produkt für das aktuelle Fenster.",
      sections: [
        {
          h2: "Häufige Fragen",
          p: "Die schnellsten Antworten auf Situationen, die die Arbeit aufhalten.",
          cards: [
            { h3: "Ich kann mich nicht anmelden", p: "Prüfen Sie die Konto-E-Mail und ob das Konto aktiv ist. Wiederholte Fehlversuche werden aus Sicherheitsgründen gedrosselt." },
            { h3: "Enterprise ist für mich deaktiviert", p: "Enterprise erfordert eine Enterprise-Rolle auf dem Konto. Bitten Sie Ihre Administration; der Selektor nennt den Grund." },
            { h3: "Ich sehe mein Projekt nicht", p: "Projekte sind über Mitgliedschaft begrenzt. Bitten Sie den Projekteigentümer, Ihr Konto hinzuzufügen." },
          ],
        },
        {
          h2: "Hilfe im Produkt",
          p: "Jedes Fenster im Arbeitsbereich hat einen eigenen Hilfe-Eintrag mit Tastenkürzeln und Definitionen für dieses Fenster.",
          cards: [
            { h3: "Tastenkürzel", p: "Öffnen Sie die Hilfe im Arbeitsbereich, um die dort verfügbaren Kürzel zu sehen." },
            { h3: "Fensterhinweise", p: "Jedes Fenster erklärt, was es zeigt und was es braucht, bevor es Daten anzeigt." },
            { h3: "Support kontaktieren", p: "Wenn die Antwort fehlt, kontaktieren Sie uns mit Projekt und Zeitpunkt des Problems." },
          ],
        },
      ],
      cta: { title: "Weiterarbeiten", text: "Melden Sie sich an und öffnen Sie Ihr Projekt.", label: "Anmelden", href: "/login?next=/environments/" },
    },
    {
      id: "faq",
      path: "faq/",
      title: "CUBI FAQ | Häufige Fragen beantwortet",
      description:
        "Antworten zu Umgebungen, Konten, Daten, Sicherheit, Zahlungen und Support der CUBI Plattform.",
      eyebrow: "FAQ",
      h1: "Die häufigsten Fragen",
      lead: "Kurze, direkte Antworten zu Konten, Umgebungen, Datenhaltung und Zahlungen.",
      sections: [
        {
          h2: "Konten und Umgebungen",
          p: "",
          cards: [
            { h3: "Brauche ich zwei Konten?", p: "Nein. Ein Konto kann beide Umgebungen öffnen, wenn es die jeweils erforderlichen Rollen trägt." },
            { h3: "Warum verlangt Enterprise eine Rolle?", p: "Enterprise zeigt organisatorische Oberflächen. Der Zugang folgt der Rolle, und der Server setzt sie durch." },
            { h3: "Kann ich die Umgebung später wechseln?", p: "Ja. Der Umgebungsselektor ist der Einstieg und zeigt nur Umgebungen, für die Ihr Konto berechtigt ist." },
          ],
        },
        {
          h2: "Daten, Sicherheit und Zahlung",
          p: "",
          cards: [
            { h3: "Wo liegen meine Projektdaten?", p: "In der Projektdatenbank des Kontos. Öffentliche Marketingseiten enthalten keine Projektdatensätze." },
            { h3: "Wer sieht ein Projekt?", p: "Nur Konten mit Mitgliedschaft in diesem Projekt innerhalb desselben Mandanten." },
            { h3: "Wann wird gezahlt?", p: "Erst nach Bestätigung durch einen konfigurierten Zahlungsanbieter. Kann die Kasse nicht starten, wird nichts belastet." },
          ],
        },
      ],
      cta: { title: "Noch eine Frage?", text: "Kontaktieren Sie uns mit Konto und Projekt.", label: "Kontakt", href: "/de/contact/" },
    },
    {
      id: "security",
      path: "security/",
      title: "CUBI Sicherheit | Identität, Zugriff und Datengrenzen",
      description:
        "Wie CUBI Identität, Sitzungen, Projektmitgliedschaft, Datengrenzen und die Trennung von öffentlichen Seiten und Projektdaten handhabt.",
      eyebrow: "SICHERHEIT",
      h1: "Sicherheit klar benannt",
      lead:
        "Diese Seite beschreibt, was das Produkt heute tatsächlich tut. Sie ist keine Zertifizierungsaussage und ersetzt keine Sicherheitsprüfung Ihrer eigenen Installation.",
      sections: [
        {
          h2: "Identität und Sitzungen",
          p: "Zugang beginnt mit einem authentifizierten Konto und einer serverseitigen Sitzung.",
          cards: [
            { h3: "Passwortbehandlung", p: "Passwörter werden als gesalzene scrypt-Hashes gespeichert, nie im Klartext." },
            { h3: "Sitzungsbehandlung", p: "Sitzungen nutzen HttpOnly-Cookies mit CSRF-Schutz bei zustandsändernden Anfragen." },
            { h3: "Anmeldedrosselung", p: "Wiederholte Fehlanmeldungen werden begrenzt, um Rateversuche zu verlangsamen." },
          ],
        },
        {
          h2: "Datengrenzen",
          p: "Projektdaten sind nach Mandant und Projekt getrennt und werden auf dem Server durchgesetzt.",
          cards: [
            { h3: "Mandant und Projekt", p: "Jedes Lesen und Schreiben ist auf Mandant und Mitgliedschaft des Kontos begrenzt." },
            { h3: "Rollenbasierter Zugriff", p: "Umgebungs- und Aktionszugriff folgt den serverseitig geprüften Rollen, nicht den angezeigten Schaltflächen." },
            { h3: "Öffentlich und privat", p: "Marketingseiten sind statisch; Projektdaten liefert nur die authentifizierte Laufzeit." },
          ],
        },
      ],
      cta: { title: "Sicherheit prüfen", text: "Details zu Identität und Zugriff in der Dokumentation.", label: "Dokumentation", href: "/de/documentation/" },
    },
    {
      id: "payments",
      path: "payments/",
      title: "CUBI Zahlungen | Pro-Abonnement und klare Abrechnung",
      description:
        "Verstehen, wie das CUBI Pro Abonnement funktioniert, was ein Kauf hinzufügt und wann tatsächlich gezahlt wird.",
      eyebrow: "ZAHLUNGEN",
      h1: "Klare Abrechnung, keine Überraschungen",
      lead:
        "CUBI Pro wird in Monatseinheiten erworben. Der Server bestätigt und verbucht den Anspruch nach einer verifizierten Zahlung, nicht die Seite.",
      sections: [
        {
          h2: "So funktioniert ein Kauf",
          p: "Sie wählen die Monate, prüfen die geschätzte Summe und gehen zur Kasse. Die Seite selbst belastet nichts.",
          cards: [
            { h3: "Monatseinheiten", p: "Zwölf Monate bedeutet zwölf gemeinsam erworbene Monatseinheiten, kein separates Jahresangebot." },
            { h3: "Bestehende Abonnements", p: "Ein bestätigter Kauf verlängert das bestehende Ablaufdatum statt neu zu beginnen." },
            { h3: "Kein Anbieter, keine Zahlung", p: "Ist kein verifizierter Anbieter konfiguriert, startet die Kasse nicht und es wird nichts belastet." },
          ],
        },
        {
          h2: "Klarheit und Nachweise",
          p: "Preise und Ansprüche werden explizit erfasst, damit spätere Fragen aus dem Datensatz beantwortet werden können.",
          cards: [
            { h3: "Arbeitspreis", p: "Der konfigurierte Arbeitspreis wird vor dem Wechsel zur Kasse angezeigt." },
            { h3: "Anspruch auf dem Server", p: "Nur der Server verbucht den Anspruch; der Browser kann ihn nicht gewähren." },
            { h3: "Erstattungen und Fragen", p: "Kontaktieren Sie uns mit Konto und Zahlungsreferenz für Abrechnungsfragen." },
          ],
        },
      ],
      cta: { title: "Pro erwerben", text: "Die Kasse läuft auf der englischen Seite.", label: "Zur Kasse", href: "/pricing/" },
    },
    {
      id: "get-started",
      path: "get-started/",
      title: "Erste Schritte mit CUBI | Ihr erstes Projekt öffnen",
      description:
        "Anmelden, die für Ihr Konto berechtigte Umgebung wählen und ein Projekt im CUBI-Arbeitsbereich öffnen.",
      eyebrow: "ERSTE SCHRITTE",
      h1: "Drei Schritte zum ersten Projekt",
      lead:
        "CUBI trennt die öffentliche Seite vom authentifizierten Arbeitsbereich. Nur die Anmeldung öffnet Projektdaten.",
      sections: [
        {
          h2: "Der Weg hinein",
          p: "Jeder Schritt ist explizit, damit Sie immer wissen, in welcher Umgebung und welchem Projekt Sie arbeiten.",
          cards: [
            { h3: "1. Anmelden", p: "Nutzen Sie Ihr CUBI-Konto. Fehlversuche werden gedrosselt; ein falsches Passwort öffnet nie einen Arbeitsbereich." },
            { h3: "2. Umgebung wählen", p: "Der Selektor zeigt Engineering und Enterprise nur, wenn Ihre Rollen sie erlauben." },
            { h3: "3. Projekt öffnen", p: "Wählen Sie ein Projekt, in dem Sie Mitglied sind. Der Arbeitsbereich öffnet sich auf dieses Projekt begrenzt." },
          ],
        },
        {
          h2: "Wenn etwas fehlt",
          p: "Zugang ist ein Datensatz, kein Raten. Jedes fehlende Element hat eine benannte Ursache.",
          cards: [
            { h3: "Kein Projekt gelistet", p: "Ihr Konto ist noch nicht Mitglied eines Projekts. Bitten Sie einen Projekteigentümer, Sie hinzuzufügen." },
            { h3: "Enterprise deaktiviert", p: "Ihrem Konto fehlt eine Enterprise-Rolle. Eine Administration kann sie vergeben." },
            { h3: "Mehr Details nötig", p: "Das Help Center erklärt die häufigen Fälle und den Weg zum Support." },
          ],
        },
      ],
      cta: { title: "Jetzt starten", text: "Melden Sie sich an und öffnen Sie Ihr erstes Projekt.", label: "Anmelden", href: "/login?next=/environments/" },
    },
    {
      id: "privacy",
      path: "privacy/",
      title: "CUBI Datenschutz | Was wir erheben und warum",
      description:
        "Was die CUBI Plattform erhebt, warum es erhoben wird und wie Projekt- und Kontodaten getrennt sind.",
      eyebrow: "DATENSCHUTZ",
      h1: "Datenschutz in klarer Sprache",
      lead:
        "Diese Seite erklärt, welche Daten das Produkt verarbeitet, damit Sie entscheiden können, was Sie teilen. Sie ist eine Produktbeschreibung, keine Rechtsberatung.",
      sections: [
        {
          h2: "Kontodaten",
          p: "Wir speichern, was nötig ist, um Sie zu authentifizieren und den Arbeitsbereich zu betreiben.",
          cards: [
            { h3: "Identität", p: "Konto-E-Mail, ein gesalzener Passwort-Hash und die dem Konto vergebenen Rollen." },
            { h3: "Sitzungen", p: "Sitzungskennungen, die Sie angemeldet halten, und die beim Abmelden ungültig werden." },
            { h3: "Betriebsprotokolle", p: "Datensätze zur Absicherung des Dienstes und zur Diagnose von Fehlern." },
          ],
        },
        {
          h2: "Projektdaten",
          p: "Projektdatensätze gehören dem Mandanten, der sie erzeugt hat.",
          cards: [
            { h3: "Mandantentrennung", p: "Projektdatensätze eines Mandanten werden keinem anderen Mandanten geliefert." },
            { h3: "Mitgliedschaft", p: "Innerhalb eines Mandanten können nur Projektmitglieder die Datensätze lesen oder schreiben." },
            { h3: "Öffentliche Seiten", p: "Marketingseiten sind statisch und enthalten keine Projektdatensätze." },
          ],
        },
      ],
      cta: { title: "Fragen zum Datenschutz?", text: "Kontaktieren Sie uns mit Konto und Anliegen.", label: "Kontakt", href: "/de/contact/" },
    },
    {
      id: "terms",
      path: "terms/",
      title: "CUBI Bedingungen | Nutzung der Plattform",
      description:
        "Die Bedingungen für die zulässige Nutzung der CUBI Plattform, Kontoverantwortung und Dienstgrenzen.",
      eyebrow: "BEDINGUNGEN",
      h1: "Nutzungsbedingungen",
      lead:
        "Diese Bedingungen beschreiben, wie die Plattform genutzt werden darf. Sie sind zum Lesen geschrieben, nicht zum Verstecken.",
      sections: [
        {
          h2: "Ihr Konto",
          p: "Sie verantworten das Konto, das Sie nutzen, und die Daten, die Sie darin ablegen.",
          cards: [
            { h3: "Kontoverantwortung", p: "Halten Sie Anmeldedaten geheim und informieren Sie uns umgehend bei vermisstem Missbrauch." },
            { h3: "Autorisierter Zugriff", p: "Greifen Sie nur auf Projekte und Umgebungen zu, die Ihnen vergeben wurden." },
            { h3: "Korrekte Daten", p: "Projektentscheidungen beruhen auf erfassten Daten; tragen Sie Datensätze ehrlich ein." },
          ],
        },
        {
          h2: "Der Dienst",
          p: "Die Plattform wird wie beschrieben bereitgestellt, mit benannten Grenzen, wo sie bestehen.",
          cards: [
            { h3: "Verfügbarkeit", p: "Wir arbeiten an der Verfügbarkeit und erklären geplante Unterbrechungen, wo möglich." },
            { h3: "Änderungen", p: "Funktionen können sich ändern; die Dokumentation nennt die Umgebung, für die eine Fähigkeit gilt." },
            { h3: "Nutzungsende", p: "Sie können die Nutzung jederzeit beenden; Ihre Daten bleiben der Datenschutzbeschreibung unterworfen." },
          ],
        },
      ],
      cta: { title: "Fragen zu den Bedingungen?", text: "Kontaktieren Sie uns mit Konto und Anliegen.", label: "Kontakt", href: "/de/contact/" },
    },
    {
      id: "about",
      path: "about/",
      title: "Über CUBI | Projekte planen und steuern",
      description:
        "CUBI verbindet Planung, Projektsteuerung, Ressourcen, Kosten und Dokumente für Bauprojekte in einem Arbeitsbereich.",
      eyebrow: "ÜBER UNS",
      h1: "Für Teams, die den Plan liefern",
      lead:
        "Bauprojekte scheitern selten an fehlenden Daten, sondern an getrennten Systemen. CUBI führt Plan, Nachweise und Entscheidungen an einem Ort zusammen.",
      sections: [
        {
          h2: "Was wir bauen",
          p: "Ein Arbeitsbereich, in dem jede Funktion denselben Projekt-, Kalender- und Aktivitätsdatensatz liest.",
          cards: [
            { h3: "Verbundene Daten", p: "Eine Änderung im Plan ist dort sichtbar, wo sie zählt." },
            { h3: "Nachvollziehbarkeit", p: "Datensätze bleiben bei den Aktivitäten und Entscheidungen, die sie erklären." },
            { h3: "Ehrliche Grenzen", p: "Was das Produkt nicht tut, wird benannt statt verschleiert." },
          ],
        },
        {
          h2: "Wie wir arbeiten",
          p: "Öffentliche Seiten informieren; Projektdaten liegen ausschließlich im authentifizierten Arbeitsbereich.",
          cards: [
            { h3: "Klare Rollen", p: "Zugriff folgt den Rollen, die der Server prüft." },
            { h3: "Nachweise", p: "Jede Aussage stützt sich auf Daten, die das Produkt tatsächlich führt." },
            { h3: "Kontakt", p: "Fragen zu Konto oder Projektszenario beantworten wir direkt." },
          ],
        },
      ],
      cta: { title: "Sprechen Sie mit uns", text: "Erzählen Sie uns von Ihrem Projektszenario.", label: "Kontakt", href: "/de/contact/" },
    },
  ],
};
