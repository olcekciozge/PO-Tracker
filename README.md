# PO Tracker — Program Outcome Management System

CSE 311 Software & CSE 321 Data Systems · Team Project · Fall 2026
Acıbadem University, Computer Engineering

A web-based system to manage and maintain the Program Outcome (PO) scores of each student.
Grades on assessments roll up into Learning Outcome (LO) scores, which roll up into PO scores.

## Team

| Member | Role | Owns |
|---|---|---|
| _Rümeysa_ | Data model | `outcomes`, `courses`, `grades` apps, score calculation |
| _Batuhan_ | Architecture & infrastructure | Project setup, PostgreSQL, settings, CI (GitHub Actions) |
| _Buğra_ | Scrum Master & access control | Backlog, sprints, velocity, `accounts` app (roles, login) |
| _Özge_ | UI/UX | Wireframes, templates, `dashboard` app, charts |

Stack: Python + Django, PostgreSQL.

## Design decisions

### User roles

| Role | Can do | Can see |
|---|---|---|
| **Admin** | Create users, create courses, assign instructors | Everything |
| **Department Head** | Enter and edit the 11 Program Outcomes | PO reports for all students and courses |
| **Instructor** | Define assessments and their weights, define LOs, set Assessment→LO and LO→PO weights, enter grades (manually or CSV upload) | Their own courses and students |
| **Student** | — (read only) | Their own grades, LO scores and PO profile |

### Who enters what

- **Program Outcomes:** Department Head (once, department-wide; 11 POs).
- **Courses:** Admin creates the course offering and assigns the instructor.
- **Learning Outcomes:** Instructor of the course.
- **Percentages / weights:** Instructor of the course.
- **Grades:** Instructor, after each assessment, via a form or CSV upload.

## Data model (agreed entities)

| Entity | Key fields | Notes |
|---|---|---|
| User | username, name, role | role ∈ {admin, head, instructor, student} |
| ProgramOutcome | code (PO1…PO11), description | Department-wide |
| Course | code, title, term, instructor → User | One row per offering, e.g. CSE 311 Fall 2026 |
| Assessment | course → Course, name, weight % | e.g. Midterm I 25%, Project 40% |
| LearningOutcome | course → Course, code, description | |
| AssessmentLO | assessment → Assessment, lo → LearningOutcome, weight % | How much an assessment feeds an LO |
| LOPO | lo → LearningOutcome, po → ProgramOutcome, weight 1–5 | How much an LO feeds a PO |
| Enrollment | student → User, course → Course | |
| Grade | student → User, assessment → Assessment, score 0–100 | Unique per (student, assessment) |

### Relationships

- Course 1 — N Assessment
- Course 1 — N LearningOutcome
- Assessment N — M LearningOutcome (through AssessmentLO)
- LearningOutcome N — M ProgramOutcome (through LOPO)
- Student N — M Course (through Enrollment)
- Student + Assessment → one Grade

### Score rule

At every level: `score = Σ (weight × score) ÷ Σ weights`

Example (Elif): Midterm 90, Project 80
→ LO1 = (90×0.6 + 80×0.4) ÷ 1.0 = 86.0, LO2 = (90×0.4 + 80×1.0) ÷ 1.4 = 82.9
→ PO1 = (86.0×1.0 + 82.9×0.5) ÷ 1.5 = 85.0, PO2 = 82.9

## Project structure

| App        | Owner | Contents |
|------------|---|---|
| `accounts` | Buğra | User, roles, login, permissions |
| `outcomes`   | Rümeysa | ProgramOutcome, LearningOutcome, LOPO, AssessmentLO |
| `courses`    | Rümeysa | Course, Assessment, Enrollment |
| `grades`   | Rümeysa | Grade, score calculation |
| `dashboard` | Özge | Pages, templates, charts |

Rule: work only in the apps you own; changes to someone else's app go through a pull request they review.

## Workflow

- Branches: `main` (stable), `develop` (integration), `feature/<short-name>` per task.
- Every change goes in through a pull request into `develop`.
- Everyone commits from their own GitHub account.
- Backlog and sprints: GitHub Projects board linked to this repo.
