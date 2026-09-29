# Critical Thinking Review: FORGE Talent Connections

Date: 2026-09-29. Scope: the demonstration application (Flutter, `lib/`),
the public landing page (`index.html`), and the working practice around
them. Method: the four frameworks the owner supplied (First Principles,
AI-CRITIQUE, the Junior Intern Model, and the Paul-Elder Elements of
Reasoning), each executed against the product as it exists in the
repository today, with every finding either acted on in this round,
scheduled, or handed to the owner as a decision. Nothing in this document
is a statistic; there are none to report.

## 1. First Principles Thinking

**The real goal.** Connect Talent with Opportunity through provable trust,
where trust means a completed, accepted collaboration and the proof it
leaves behind, vouched for by two humans who put their names on it.
Everything else in the product is a means to that.

**Assumptions listed, then challenged.**

| Assumption the product had been carrying | Fundamental? | Decision |
|---|---|---|
| A visitor must be able to open the application from the public page to understand it | No. The page must convey the product; the product is not the page's proof | Removed every link to the application from the landing page (owner's intellectual property concern). The page now describes and shows, and its single door is Request Consideration |
| Thirty screens make the product clearer | No. Breadth without the core loop makes it harder to see what must be true | Added the five-step core loop (Invitation, Proof, Vouch, Project, Sealed Record) to the Mission screen and the dashboard so no feature is met without knowing which step it serves |
| AI matching is a headline feature | No. It is a suggestion engine subordinate to the two-human rule | Kept; every AI surface now carries the review card (section 2) that says so on the surface itself |
| A phone build needs a native app | No. The home-screen web app already delivers the phone experience; native is a distribution choice | Documented in `docs/IPHONE_DEMO.md`; native build routes prepared, not required |
| The marketing video can be improved by processing | No. Detail comes from the source | Restored the original and cleaned it; any further gain needs the master file |

**Rebuilt solution.** The product is one loop and one rule. The loop is
the five steps above. The rule is that nothing opens without proof and two
humans decide at every step. This round made both visible where a person
first arrives (Mission, dashboard) and where a person is most likely to
over-trust a machine (every AI output).

## 2. AI-CRITIQUE Framework

The product's own outputs are AI-built, and the product itself contains
AI outputs (match suggestions, the assistant, the Talent Signature). The
framework was applied in both directions.

**Applied to the product's AI surfaces.** Each surface now shows a
"Before You Use This" card with eight lines, one per letter, in the
product's language:

| Letter | Check | The product's answer |
|---|---|---|
| A | Accurate | Built only from verified records, never claims |
| I | Intent | Answers what you asked, not what is easiest |
| C | Complete | Says plainly what it does not know |
| R | Relevant | Tied to this project, not a generic profile |
| I | Independent | Names every source; never one unnamed source |
| T | Tone | Plain language; no promises, no pressure |
| Q | Question It | Ask the reviewer anything it left out |
| U | Use | A suggestion only; two humans decide |

Placed on the AI match screen (before Pass and Apply to Project), the AI
Assistant (before its production note), and the Talent Signature (after
"What this never does"). The card is a shared widget
(`lib/widgets/ai_output_review.dart`) and appears in the Widget Gallery.

**Applied to this engineering work.**

- Accuracy: the landing page carries no statistic, no testimonial, no
  partner name. The video is labelled AI-generated. The road-ahead
  timeline uses the owner's wording and no dates.
- Intent: the owner's latest intent is that the public page shows the
  product without exposing it. Done this round.
- Completeness: the page lacked any statement of the core loop; the
  Mission screen and dashboard lacked it too. Added.
- Relevance: the "Try the Demo" buttons were relevant to a reviewer, not
  to the audience the page now serves. Removed.
- Independence: this work has had one author, an AI. The owner should have
  one human outside the project read the landing page and use the
  application for ten minutes before launch. That review is the single
  most valuable check still missing, and no framework run by the same
  author substitutes for it.
- Tone: the page and the application use the same vocabulary and the same
  refusal to promise outcomes.
- Improvement: the largest remaining gains are outside the code: the
  full-resolution video master, and the live backend behind the fixtures.
- Questions: listed in section 5.
- Safe to use: the page collects nothing; its only action is an email
  link. The application runs on fixtures and writes nothing.

## 3. The Junior Intern Model

The owner directs AI as the builder. This round tightened the brief in both
directions.

- **Clear brief and context.** The Codex brief delivered on 2026-09-26
  names every source file, every token, every language rule, and the
  verification protocol. In the application, the assistant's input now
  asks for a brief the way a good manager would: "Your goal, who it is
  for, and the format you want".
- **Examples of good.** The design system document and the Mission screen
  are the examples of good; both are referenced by path in the brief.
- **Review and correct.** Every round in this repository ends with the
  same gate: format, analyzer, the full test suite, and a visual check.
  This round added tests for the two new widgets, including a reflow check
  at twice the text size.
- **Iterate until it meets the standard.** The standard is written down:
  Title Case titles (guard-tested), barred vocabulary (guard-tested), no
  percentages of success, the two-human rule in every AI surface (now on
  the surface itself).

## 4. Paul-Elder Elements of Reasoning

| Element | For FORGE Talent Connections |
|---|---|
| Purpose | Let real work become proof that travels with a person, and let two humans, not a system, open every door |
| Question at issue | Can trust between strangers be built from verified collaboration rather than from claims, credentials, or algorithms? |
| Information | Verified deliverables, sealed credentials, vouches with names attached, and the project's own requirements. Nothing self-reported carries weight |
| Assumptions | That institutions will convene projects; that Talent will accept a slower, proof-first path; that sponsors value provable work over volume. Each is a hypothesis for the pilot, not a fact |
| Interpretation and inference | A suggestion is an inference from records; the product shows every factor for and against and sends borderline cases to a named human |
| Concepts | Talent, Opportunity, Institution, Veteran, invitation, proof, vouch, project, sealed record |
| Point of view | Built from the person's side: the record belongs to them, the export is theirs, and no system can accept, reject, pay, or publish on their behalf |
| Implications | If it works, a Veteran or a first-generation student carries proof no résumé can; if the two-human rule is ever bypassed for speed, the product becomes the job board it refuses to be |

The last implication is the one to guard. Every future feature should be
asked one question first: does it keep two humans in the decision, or does
it quietly remove one?

## 5. Questions for the owner (decisions only you can make)

1. Outside review: who is the one person outside the project who will read
   the page and use the application before launch?
2. The tagline appears once in the strategy record as "through Project
   Collaboration". The product and page use "through Collaboration". Which
   is final?
3. The road-ahead timeline has no dates. Should it?
4. The full-resolution video master: does one exist, and where?
5. The public page no longer links to the application. Should the
   Request Consideration email mention that a walkthrough is available on
   request?

## 6. What changed in this round

- New: `lib/widgets/ai_output_review.dart`, `lib/widgets/core_loop_strip.dart`, with tests.
- AI match, AI Assistant, and Talent Signature screens carry the review card; the assistant asks for a clear brief.
- Mission and dashboard carry the core loop.
- Landing page: no link, address, or mention of the demonstration application; the door is Request Consideration; the video keeps a single relative source.
- This document.
