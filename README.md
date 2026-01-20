# Anki Vibe

**Anki Vibe** is a powerful CLI middleware that allows you to manage your [Anki](https://apps.ankiweb.net/) collections using **Code-as-Source-of-Truth**.

It enables you to treat your knowledge base like a software project: use Git for version control, edit flashcards in your favorite text editor (VS Code, Cursor, etc.), and synchronize changes seamlessly with Anki.

![Anki Vibe Banner](https://img.shields.io/badge/Anki-Vibe-blue) ![Python](https://img.shields.io/badge/Python-3.10%2B-yellow) ![License](https://img.shields.io/badge/License-MIT-green)

## 🌟 Key Features

*   **Project-based Workflow:** Create isolated projects for specific topics (e.g., "JLPT N5", "Medical Terminology") without syncing your entire Anki collection.
*   **Code-as-Source-of-Truth:** Your YAML/Markdown files are the master copy.
*   **Git-Friendly:** Designed to work perfectly with Git. Review changes with `git diff` before pushing to Anki.
*   **Smart Sync:** Uses **SQLite** based state tracking and Hash comparison to update only changed notes, ensuring speed and efficiency.
*   **Scoped Pull:** Pull only the specific decks or note types you need using powerful Anki queries.
*   **Round-trip Editing:**
    *   **Push:** Edit YAML -> Sync to Anki.
    *   **Pull:** Edit in Anki -> Pull to YAML (preserves comments and formatting).

---

## 🚀 Installation

### Prerequisites

1.  **Anki Desktop**: Installed and running.
2.  **AnkiConnect**: Install this add-on in Anki (Code: `2055492159`).
3.  **Python 3.10+**: Installed on your system.

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/hieucao/anki-vibe.git
    cd anki-vibe
    ```

2.  **Install dependencies (using Poetry):**
    ```bash
    pip install poetry
    poetry install
    ```

3.  **Setup System-wide Command (Optional but Recommended):**
    This allows you to run `anki-vibe` from any terminal directory.
    ```bash
    mkdir -p ~/.local/bin
    # Create a wrapper script
    echo '#!/bin/bash' > ~/.local/bin/anki-vibe
    echo '"'$(pwd)/.venv/bin/python'" "'$(pwd)/src/main.py'" "$@"' >> ~/.local/bin/anki-vibe
    chmod +x ~/.local/bin/anki-vibe
    
    # Add to PATH (if not already)
    export PATH=$PATH:~/.local/bin
    ```

---

## 📖 Quick Start (Project-based Workflow)

The recommended way to use Anki Vibe is creating a dedicated folder for your specific study topic.

### 1. Initialize a Project

Create a new directory and initialize it:

```bash
mkdir my-vocab-project
cd my-vocab-project
anki-vibe init --name "My Vocab Project" --profile "User 1"
```

This creates an `anki-vibe.toml` configuration file.

### 2. Configure Your Project

Edit `anki-vibe.toml` to define what you want to manage.

```toml
[project]
name = "My Vocab Project"
anki_profile = "User 1"  # Your Anki profile name

[[targets]]
name = "Vocabulary Deck"
model = "Basic"                 # Note Type in Anki
deck = "My::Vocabulary"         # Deck to store notes
query = 'deck:"My::Vocabulary"' # Query to pull existing notes
folder = "data/vocab"           # Where to save YAML files
```

### 3. Pull Existing Data

Fetch current notes from Anki based on your configuration:

```bash
anki-vibe pull
```

### 4. Edit or Create Notes

Open the generated `data/vocab/notes.yaml` file. You can add new notes or edit existing ones.

```yaml
- id: null  # New note (ID will be assigned after sync)
  deck: My::Vocabulary
  tags: [new_word]
  fields:
    Front: "Hello"
    Back: "Xin chào"
```

### 5. Sync Changes to Anki

Push your changes back to Anki:

```bash
anki-vibe sync
```

---

## 🔧 Commands

| Command | Description |
| :--- | :--- |
| `anki-vibe init` | Initialize a new project in the current directory. |
| `anki-vibe pull` | Fetch data from Anki based on `anki-vibe.toml` (or all data if `--profile` is used). |
| `anki-vibe sync` | Push local changes to Anki. Updates changed notes only. |
| `anki-vibe info` | Show connection status and available decks. |

**Options:**
- `--yes` / `-y`: Skip confirmation prompts (useful for scripts).
- `--dry-run`: Simulate sync without modifying Anki (Sync only).
- `--profile`: Force legacy mode (Monorepo) targeting a specific profile.

---

## 📂 Architecture

Anki Vibe supports two modes:

1.  **Project Mode (Recommended):**
    *   Context defined by `anki-vibe.toml` in the current directory.
    *   State tracked in local `.anki_vibe.db`.
    *   Only pulls/syncs specific targets defined in config.

2.  **Monorepo Mode (Legacy):**
    *   Targeted by `anki-vibe sync --profile <Name>`.
    *   Syncs **ALL** models and decks in that profile.
    *   Data stored in centralized `data/anki/<Profile>` folder.

For detailed architecture, see [docs/architecture_and_workflow.md](docs/architecture_and_workflow.md).